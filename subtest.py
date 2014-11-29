#!/usr/bin/python


from os import listdir,walk,stat
from os.path import isfile, isdir, join, getsize, basename
import re
import sys
import traceback
import os
import urllib

TARGET_FOLDER = '/var/media/jemenake/Movies'
TEMP_FOLDER = '/tmp'

srt_codes = {
	'chinese': 'cn',
	'english': 'en',
	'french': 'fr',
	'german': 'de',
	'portuguese': 'pt',
	'russian': 'ru',
	'spanish': 'es'
	}


##########################################
##########################################
def get_files_and_folders(folder):
	folders = []
	files = []
	for (dirpath, dirnames, filenames) in walk(folder):
		folders.extend( [ join(dirpath,d) for d in dirnames ] )
		files.extend( [ join(dirpath,f) for f in filenames ] )
	return(files,folders)


##########################################
##########################################
#
# Returns a tuple: movie_creation_succeeded, should_delete_source_files, textual_message
def process(folder,nzbname,jobname,reportnum,category,newsgroup,status):
	if int(status) != 0:
		return False, False, "SABNZBD status wasn't zero"

	(files,folders) = get_files_and_folders(folder)

	if len(files) < 1:
		return False, True, "Didn't find any files"

#	print "=== Checking if it looks like a trojan ==="
	# Check for trojan stuff (like Codec/setup.exe, etc...)
	if looks_like_trojan(files):
		return False, True, "Looks like a trojan"



#########################################
#########################################
def get_subtitles(filename):
######################################
# Extract the act descriptions from the HTML. Returns the results as
# a list of dicts. The dictionary keys are 'head' and 'body'. For example:
# [ { 'head' : 'Prologue', 'body' : 'Ira talks' }, { 'head' : 'Act 1', 'body' : ... } ... ]
#
	url = "http://www.opensubtitles.org/en/search/imdbid-337692/sublanguageid-all"
	page = urllib.urlopen(url).read()

	os_codes = { 'en' : 'eng', 'sp' : 'spa' }
	URL = "http://www.opensubtitles.org/en/search/imdbid-{0}/sublanguageid-{1}".format(imdb_num, os_codes[lang])
	URL = "http://www.opensubtitles.org/en/search/sublanguageid-{0}/moviename-{1}".format(os_codes[lang], urllib.quote(title))

# Example table row:
#<tr onclick="servOC(5453405,'/en/subtitles/5453405/on-the-road-es/short-on', '#DCF2B8')" id="name5453405" class="change even expandable">
#	<td class="sb_star_even" id="main5453405">
#		<strong>
#			<a class="bnone" onclick="reLink(event,'/en/subtitles/5453405/on-the-road-es');" title="subtitles - On the Road" href="/en/subtitles/5453405/on-the-road-es">
#				On the Road (2012)
#			</a>
#		</strong>
#		<br />
#		On.The.Road.2012.LIMITED.DVDRip.XviD-Larceny
#		<br />
#		<a rel="nofollow" onclick="rdr(this);" class="p a a_1" href="/en/pcsuekykxojmispbrfkpnivdq" title="On the Road - Download at 25 MBit">
#			Download at 25 MBit
#		</a>
#		<a style="margin-left:7px" class="p a a_2" onclick="rdr(this);" href="http://www.opensubtitles.net/opensubtitles-player" title="Download Subtitles Player">
#			Download Subtitles Player
#		</a>
#	</td>
#	<td align="center" style="padding-left:7px;">
#		<a title="Spanish" href="/en/search/imdbid-337692/sublanguageid-spa" onclick="reLink(event,'/en/search/imdbid-337692/sublanguageid-spa');">
#			<div class="flag es"></div>
#		</a>
#	</td>
#	<td align="center">
#		1CD
#	</td>
#	<td align="center" title="11:27:15">
#		22/12/2013
#		<br />
#		<span class="p">25.000</span>
#	</td>
#	<td align="center">
#		<a href="/en/subtitleserve/sub/5453405" onclick="reLink(event,'/en/subtitleserve/sub/5453405');">
#			251x
#		</a>
#		<br />
#		<span class="p">srt</span>
#	</td>
#	<td align="center">
#		0.0
#	</td>
#	<td align="center">
#		0
#	</td>
#	<td align="center">
#		<a title="20963 (votes)" href="/redirect/http://www.imdb.com/title/tt0337692/" onclick="reLink(event,'/redirect/http://www.imdb.com/title/tt0337692/');">
#			6.0
#		</a>
#	</td>
#	<td>
#		<a href="/en/profile/iduser-1561722" onclick="reLink(event,'/en/profile/iduser-1561722');">
#			robot2xl
#		</a>
#		<br />
#		<a class="none" style="color:#aaa" onclick="reLink(event,'/en/support#ranks');" href="/en/support#ranks" title="platinum member">
#i			<img width="100" height="20" src="http://static.opensubtitles.org/gfx/icons/ranks/platinum_member.png" title="platinum member" alt="platinum member" />
#		</a>
#	</td>
#</tr>
#<tr style="display:none" id="ihtr5453405">
#	<td style="background:#ECECD9;" colspan="9">
#		<table style="width:100%;" cellspacing="0" cellpadding="0" border="0">
#			<tr>
#				<td style="border:1px solid #003366">
#					<iframe style="width:100%; border:0px;" id="ihif5453405"></iframe>
#				</td>
#			</tr>
#		</table>
#	</td>
#</tr>


#########################################
#########################################
def main():	

	files, folders = get_files_and_folders('.')

	files = [a for a in files if a[:6]]

	for filename in files:
		with open(filename) as f:
			print "Processing {0}".format(file)
			(folder,nzbname,jobname,reportnum,category,newsgroup,status) = [ s.strip() for s in f.readlines()[:7] ]
			print folder
			# try:
			# 	success,cleanup,message = process(folder,nzbname,jobname,reportnum,category,newsgroup,status)
			# 	if cleanup:
			# 		if TEST_MODE:
			# 			print "Test mode is on. We would have deleted thedownloaded files"
			# 		else:
			# 			print "Removng downloaded files"
			# 			if isfile(filename):
			# 				os.remove(filename)
			# 			if isdir(folder):
			# 				shutil.rmtree(folder)
			# 	print message
			# except:
			# 	print "FAILED on {0} because:".format(nzbname)
			# 	print sys.exc_info()[1]
			# 	traceback.print_tb(sys.exc_info()[2])
			print "==============="

if __name__ == "__main__":
	main()
