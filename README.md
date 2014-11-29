PlexMovieProcessor
==================

A python script to identify/rename/transcode/subtitle downloaded movies for Plex

This program was, originally, written for a system using CouchPotato, SABNZBD, and Plex.
The program aims to solve a few problems with this system:

** Some movies aren't in a format suitable for Plex (they're VIDEO_TS, or some strange .avi file)

** Some movies are in a bitrate which is too fast (for people watching Plex from a server over the internet)

** Some movie downloads are actually just trojan files (a garbage .avi file accompanied by a "setup.exe" file claiming to be the needed codec)

** Some movie downloads don't come with subtitles. Or, if they do, they're not named in a way which Plex understands.

** Some movie files are named something strange which Plex cannot figure out


PlexMovieProcessor aims to solve these issues.

** If the movie is not in a suitable format (like a .mkv or .mp4), is it transcoded

** If the movie has too high of a bitrate, it is transcoded

** It tries to detect if the movie is accompanied by trojan-like files

** It tries to find any included SRT files and name them appropriately. If it can't find all SRT files which the user wants, it searches online subtitle databases for a suitable one.

** It tries to deduce the name and year of the movie and name it "title (year).mkv"
