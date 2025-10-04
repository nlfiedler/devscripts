#!/bin/bash
#
# Replicate a ZFS data set to another in a repeatable fashion using snapshots
# and replication streams (zfs send | zfs recv). Can send the data set to a
# remote host using SSH.
#
# Preparation
#
# $ ssh-copy-id -i ~/.ssh/id_rsa hostaddr
# $ sudo su -
# # ssh-copy-id -i .ssh/id_rsa.pub username@hostaddr
#
# Troubleshooting
#
# "target zfs dataset <dataset> is not present"
#    The SSH connection is not set up correctly, see above.
#
# "<username>@<hostaddr>'s password:"
#    The SSH connection is not set up correctly, see above.
#
MONOCHROME=false
DEBUG=false
INCREMENTAL=false
SOURCE_NAME=''
TARGET_NAME=''
HOST_NAME=''
REMOTE_SUDO=false

# Print the first argument in red text on STDERR.
function error() {
    $MONOCHROME || echo -e "\033[31m$1\033[0m" >&2
    $MONOCHROME && echo -e "$1" >&2 || true
}

# Print arguments to STDERR and exit.
function die() {
    error "FATAL: $*" >&2
    exit 1
}

# Print the first argument in blue text on STDERR.
function debug() {
    $DEBUG || return 0
    $MONOCHROME || echo -e "\033[33m$1\033[0m" >&2
    $MONOCHROME && echo -e "$1" >&2 || true
}

function usage() {
    cat <<EOS

Usage:

    replica.sh --source <dataset> --target <dataset> [--remote <ssh-host>]

Description:

    Replicate the named 'source' dataset to 'target' using zfs send/rev.

    --source <dataset>
        Specify the source ZFS dataset to replicate.

    --target <dataset>
        Specify the ZFS dataset to which the replication stream will be
        sent. This dataset will be overwritten by the source.

    --remote <ssh-host>
        Name or address of the system to which the replication stream will
        be sent, using SSH.

    --remote-sudo
        Prepend the remote commands with 'sudo' (e.g. 'sudo zfs recv').

    -m
        Monochrome; no colored text.

    -h, --help
        Display this help message.

EOS
}

function read_arguments() {
    while [[ -n "$1" ]]; do
        case "$1" in
        --source)
            SOURCE_NAME=$2
            shift
            ;;
        --target)
            TARGET_NAME=$2
            shift
            ;;
        --remote)
            HOST_NAME=$2
            shift
            ;;
        --remote-sudo)
            REMOTE_SUDO=true
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        --debug)
            DEBUG=true
            ;;
        -m)
            MONOCHROME=true
            ;;
        --)
            break
            ;;
        *)
            die "Unknown option: $1"
            ;;
        esac
        shift
    done
}

# Check if second argument is found in array named in first argument.
function array_contains() { 
    local array="$1[@]"
    local seeking=$2
    local in=1
    for element in "${!array}"; do
        if [[ $element == "$seeking" ]]; then
            in=0
            break
        fi
    done
    return $in
}

# Ensure necessary utilities are already installed.
function ensure_readiness() {
    if [[ -z "${SOURCE_NAME}" ]]; then
        die 'Source dataset name is required, pass --source <dataset>'
    fi
    if [[ -z "${TARGET_NAME}" ]]; then
        die 'Target dataset name is required, pass --target <dataset>'
    fi
    if ! which zfs >/dev/null 2>&1; then
        die 'zfs is required. Please install the `zfs` package.'
    fi
}

# Ensure the named source dataset is actually present.
function ensure_source() {
    debug 'checking source dataset exists'
    # test by retrieving a setting that all ZFS datasets have
    zfs get compression ${SOURCE_NAME} >/dev/null 2>&1
    if (( $? != 0 )); then
        die "source zfs dataset ${SOURCE_NAME} is not present"
    fi
}

# Ensure the named target dataset is actually present.
function ensure_target() {
    debug 'checking target dataset exists'
    # test by retrieving a setting that all ZFS datasets have
    local CMD="zfs get compression ${TARGET_NAME} >/dev/null 2>&1"
    if [[ -n "${HOST_NAME}" ]]; then
        CMD="ssh ${HOST_NAME} ${CMD}"
    fi
    eval "${CMD}"
    if (( $? != 0 )); then
        die "target zfs dataset ${TARGET_NAME} is not present"
    fi
}

# Take a snapshot on the source with the name "replica:<datetime>"
function take_snapshot() {
    debug 'taking snapshot'
    local DATE_NOW=$(date +'%Y-%m-%d-%T')
    local TAG_NAME="replica:${DATE_NOW}"
    zfs snapshot "${SOURCE_NAME}@${TAG_NAME}"
    echo "${TAG_NAME}"
}

# Filter the input to find only our specific snapshots.
function get_snapshot_tags() {
    # partial match on our name is good enough, otherwise this regex is really really really long
    echo "$1" | awk '/@replica:[[:digit:]]{4}-[[:digit:]]{2}/ { split($1, a, "@"); print a[2] }' | sort
}

# Output a list of the source snapshots created by this script.
function our_source_snapshots() {
    debug 'gathering source snapshot list'
    local OUTPUT=$(zfs list -H -o name -r -t snapshot ${SOURCE_NAME})
    get_snapshot_tags "$OUTPUT"
}

# Output a list of the target snapshots created by this script.
function our_target_snapshots() {
    debug 'gathering target snapshot list'
    local CMD="zfs list -H -o name -r -t snapshot ${TARGET_NAME}"
    if [[ -n "${HOST_NAME}" ]]; then
        CMD="ssh ${HOST_NAME} ${CMD}"
    fi
    local OUTPUT=$(${CMD})
    get_snapshot_tags "$OUTPUT"
}

function build_recv_cmd() {
    local RECV_CMD="zfs recv -F ${TARGET_NAME}"
    if $REMOTE_SUDO; then
        RECV_CMD="sudo ${RECV_CMD}"
    fi
    if [[ -n "${HOST_NAME}" ]]; then
        RECV_CMD="ssh ${HOST_NAME} ${RECV_CMD}"
    fi
    echo "${RECV_CMD}"
}

# Send a full replication stream for the named snapshot.
function send_first_snapshot() {
    debug 'sending initial snapshot'
    zfs send -R "${SOURCE_NAME}@$1" | $(build_recv_cmd)
}

# Send an incremental replication stream for the named snapshots.
function send_incremental() {
    debug 'sending incremental snapshot'
    zfs send -R -I $1 "${SOURCE_NAME}@$2" | $(build_recv_cmd)
}

# Prune the old replica snapshots from source dataset.
function prune_source_snapshots() {
    debug 'pruning old source snapshots'
    # prune old snapshots in source file system
    if (( ${#SOURCES[*]} < 3 )); then
        return
    fi
    local OLD_SNAPS=${SOURCES[@]:0:${#SOURCES[*]}-2}
    for SNAP in $OLD_SNAPS; do
        zfs destroy "${SOURCE_NAME}@${SNAP}"
    done
}

# Prune the old replica snapshots from target dataset.
function prune_target_snapshots() {
    debug 'pruning old target snapshots'
    if (( ${#TARGETS[*]} < 3 )); then
        return
    fi
    local CMD_PREFIX=''
    if $REMOTE_SUDO; then
        CMD_PREFIX="sudo ${CMD_PREFIX}"
    fi
    if [[ -n "${HOST_NAME}" ]]; then
        CMD_PREFIX="ssh ${HOST_NAME} ${CMD_PREFIX}"
    fi
    local OLD_SNAPS=${TARGETS[@]:0:${#TARGETS[*]}-2}
    for SNAP in $OLD_SNAPS; do
        ${CMD_PREFIX}zfs destroy "${TARGET_NAME}@${SNAP}"
    done
}

function main() {
    read_arguments "$@"
    ensure_readiness
    ensure_source
    ensure_target
    TAG_NAME=$(take_snapshot)
    SOURCE_SNAPS=$(our_source_snapshots)
    readarray -t SOURCES <<< "$SOURCE_SNAPS"
    TARGET_SNAPS=$(our_target_snapshots)
    readarray -t TARGETS <<< "$TARGET_SNAPS"

    if [[ -n "${TARGET_SNAPS}" && "${#SOURCES[*]}" -gt 1 ]]; then
        if ! array_contains TARGETS "${SOURCES[-2]}"; then
            die 'Destination snapshots out of sync with source, destroy and try again.'
        fi
    fi
    if (( ${#SOURCES[*]} == 1 )); then
        # send the initial snapshot
        send_first_snapshot ${TAG_NAME}
    elif [[ -z "${TARGET_SNAPS}" ]]; then
        # send the latest snapshot since the destination has none
        send_first_snapshot ${TAG_NAME}
    else
        # destination has matching snapshots, send an incremental
        send_incremental "${SOURCES[-2]}" ${TAG_NAME}
    fi
    prune_source_snapshots
    # refetch the target snapshots for up-to-date pruning
    TARGET_SNAPS=$(our_target_snapshots)
    readarray -t TARGETS <<< "$TARGET_SNAPS"
    prune_target_snapshots
}

main "$@"
