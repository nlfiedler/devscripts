#!/usr/bin/env escript
%% -*- erlang -*-
%%
%% Fix permissions of files and directories.
%%
%% Requires getopt (https://github.com/jcomellas/getopt/) to be installed
%% in /usr/local/lib/erlang/lib (or somewhere in the load path).
%%

-include_lib("kernel/include/file.hrl").

main(Args) ->
    OptSpecList = [
        {file,    $f, "file",    {string, "644"}, "permissions for files (default 644)"},
        {dir,     $d, "dir",     {string, "755"}, "permissions for directories (default 755)"},
        {exclude, $x, "exclude", {string, ""},    "entries to ignore (comma separated)"},
        {path,    $p, "path",    {string, "."},   "path to process (default .)"}
    ],
    case getopt:parse(OptSpecList, Args) of
        {ok, {Options, _NonOptArgs}} ->
            ValidOpts = validate_args(Options),
            FilePerm = proplists:get_value(file, ValidOpts),
            DirPerm = proplists:get_value(dir, ValidOpts),
            Excludes = proplists:get_value(exclude, ValidOpts),
            Path = proplists:get_value(path, ValidOpts),
            walk_tree(Path, Excludes, DirPerm, FilePerm);
        {error, {Reason, Data}} ->
            io:format("Error: ~s ~p~n~n", [Reason, Data]),
            getopt:usage(OptSpecList, "fixperms")
    end,
    ok.

% Ensure the parsed command line arguments are valid, return
% a proplist with validated values.
validate_args(Options) ->
    FilePermStr = proplists:get_value(file, Options),
    FilePerm = (catch list_to_integer(FilePermStr, 8)),
    if not is_integer(FilePerm); FilePerm > 511; FilePerm < 256 ->
            io:format("Invalid file permissions: ~s~n", [FilePermStr]),
            exit(badarg);
        true -> ok
    end,
    DirPermStr = proplists:get_value(dir, Options),
    DirPerm = (catch list_to_integer(DirPermStr, 8)),
    if not is_integer(DirPerm); DirPerm > 511; DirPerm < 256 ->
            io:format("Invalid directory permissions: ~s~n", [DirPermStr]),
            exit(badarg);
        true -> ok
    end,
    ExcludeStr = proplists:get_value(exclude, Options),
    Excludes = re:split(ExcludeStr, ",", [{return, list}]),
    Path = proplists:get_value(path, Options),
    case filelib:is_dir(Path) of
        true  -> ok;
        false ->
            io:format("Path does not exist: ~s~n", [Path]),
            exit(badarg)
    end,
    [{file, FilePerm}, {dir, DirPerm}, {exclude, Excludes}, {path, Path}].

walk_tree(Path, Excludes, DirPerm, FilePerm) ->
    {ok, Filenames} = file:list_dir(Path),
    Filepaths = [filename:join(Path, F) || F <- Filenames],
    Files = lists:filter(fun filelib:is_regular/1, Filepaths),
    FilterDirs = fun(F) ->
        case filelib:is_dir(F) of
            true -> not lists:member(F, Excludes);
            false -> false
        end
    end,
    Dirs = lists:filter(FilterDirs, Filenames),
    [fix_perms(F, FilePerm, DirPerm) || F <- Files ++ Dirs],
    [walk_tree(F, Excludes, DirPerm, FilePerm) || F <- Dirs],
    ok.

fix_perms(F, FilePerm, DirPerm) ->
    case file:read_file_info(F) of
        {ok, #file_info{type=directory, mode=Mode}} ->
            if Mode =/= DirPerm -> file:change_mode(F, DirPerm);
                true -> ok
            end;
        {ok, #file_info{type=regular, mode=Mode}} ->
            if Mode =/= FilePerm -> file:change_mode(F, FilePerm);
                true -> ok
            end
    end,
    ok.
