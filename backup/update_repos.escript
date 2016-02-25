#!/usr/bin/env escript
%% -*- erlang -*-
%%
%% Finds and updates the Git repositories.
%%
%% This is a highly specialized script that assumes that the repositories
%% in question are bare (i.e. no working tree) and have a single remote.
%%
%% To create the initial backup repositories, clone them like so:
%%
%% $ git clone --mirror <git_url>
%%

-include_lib("kernel/include/file.hrl").

main([]) ->
    % build full paths for all entries in the current directory
    {ok, Cwd} = file:get_cwd(),
    {ok, Filenames} = file:list_dir(Cwd),
    Filepaths = [filename:join(Cwd, Name) || Name <- Filenames],

    % keep only the directories
    Directories = lists:filter(fun filelib:is_dir/1, Filepaths),

    % keep only the git repositories
    IsRepository = fun(Filepath) ->
        HeadName = filename:join(Filepath, "HEAD"),
        case file:read_file_info(HeadName) of
            {ok, _FileInfo} -> true;
            {error, enoent} -> false
        end
    end,
    Repositories = lists:filter(IsRepository, Directories),

    % run git-fetch on each remote of each repository
    lists:foreach(fun process_repo/1, Repositories).

% Fetch the latest upstream content for each remote of the repo.
process_repo(Repo) ->
    Remotes = get_remotes(Repo),
    FetchRemote = fun({Name, Url}) ->
        FetchOut = os:cmd(io_lib:format("git --git-dir='~s' fetch ~s", [Repo, Name])),
        io:format("~s", [FetchOut]),
        Dir = filename:basename(Repo),
        io:format("Fetched ~s successfully for ~s~n", [Url, Dir])
    end,
    lists:foreach(FetchRemote, Remotes).

% Extract the fetch remotes for the named repository, as a list of tuples.
get_remotes(Path) ->
    RemoteOut = os:cmd(io_lib:format("git --git-dir='~s' remote -v", [Path])),
    % remote format: Name [tab] Url [space] "(fetch)" | "(push)"
    Lines = re:split(RemoteOut, "\n", [{return, list}]),
    Remotes = lists:filter(fun(Line) -> length(Line) > 0 end, Lines),
    % extract parts of the remotes (name, url, type)
    RemoteParts = [re:split(Remote, "[\t ]", [{return, list}]) || Remote <- Remotes],
    % keep only the "(fetch)" remotes
    FetchRemotes = lists:filter(fun(Details) ->
        case Details of
            [_Name, _Url, "(fetch)"] -> true;
            _ -> false
        end
    end, RemoteParts),
    [{Name, Url} || [Name, Url, _Type] <- FetchRemotes].
