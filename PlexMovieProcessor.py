#!/usr/bin/python

from imdb import IMDb

ia = IMDb()

from os import listdir,walk,stat
from os.path import isfile, isdir, join, getsize, basename
import re
import sys
import traceback
import shutil
import os
import bs4
import urllib

TARGET_FOLDER = '/var/media/jemenake/Movies'
TEMP_FOLDER = '/tmp'

TEST_MODE = False

# MIN/MAX bitrates come out to about 500MB-1500MB for a 2-hour movie
MAX_RATE = 12000000
MIN_RATE =  4000000

srt_codes		= { 
	'chinese' : 'cn',
	'english' : 'en', 
	'french'  : 'fr', 
	'german'  : 'de', 
	'portuguese': 'pt',
	'russian' : 'ru',
	'spanish' : 'es'
	}

unwanted_language_codes = [ 'fr', 'de', 'ru', 'cn' ]


##########################################
##########################################
def transcode(source, max_size):
	import random
	import subprocess	

#	ENDING = ".mp4"
	ENDING = ".mkv"

	random.seed()
	num=random.random() * 1000000
	filename = join( TEMP_FOLDER, "transcode." + str(num) + ENDING )
	print filename
	size = max_size + 1
	quality = 20
	while size > max_size:
		quality += 2
		try:
			os.remove(filename)
		except:
			print "Caught exception"
		parms = [ 'HandBrakeCLI', '--preset', 'iPad', '-q', str(quality), '-i', source, '-o', filename ]
		subprocess.call(parms)
		size = getsize(filename)
	print "Final quality = {0}".format(quality)
	return filename

##########################################
##########################################
def get_video_ts(folders):
	for d in folders:
		if d[-9:].upper() == "/VIDEO_TS":
			return d
	return None

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
# This is for parsing a filename in the form of
# something - something - title (year) - something.ext
def parse_title_type_2(filename):
	chunks = [ a.strip() for a in filename.split('-') ]
	regex = r'^(.*) *\(?([0-9]{4})\)?'
	for chunk in chunks:
#		print "Trying chunk: " + chunk
		m = re.search(regex,chunk)
		if m != None:
			name = m.group(1)
			year = m.group(2)
			print "parse_title_type_2 thinks Name: {0}  year: {1}".format(name,year)

##########################################
##########################################
def deduce_title(filename):
	# Usually, the name will be of the format:
	#	Name.Name.Name.Year.xVID.x264.AAC.mkv
	# So, find the year, and then grab everything before that.
	filename = basename(filename)
	filename = filename.replace('.',' ')
	parse_title_type_2(filename)

	regex = r'(^|/)([^/]*)[. ](19[0-9]{2}|20[0-9]{2})[. ]([^/]*)'
	m = re.search(regex,filename)
	if m != None:
#		print "Name = {0}".format(m.group(2))
#		print "Year = {0}".format(m.group(3))
		name = m.group(2)
		year = m.group(3)
		# Check for trailing articles, like "the" or "an"
		pieces = re.split('[. ]',name)
		if pieces[-1].lower() in [ 'a', 'an', 'the' ]:
			print "@@@@@@@@@@@@@@@@@@@@@"
			print "@@@@@@@@@@@@@@@@@@@@@"
			print "@@@@@@@@@@@@@@@@@@@@@"
			print name + " ends with " +  pieces[-1]
			pieces.insert(0,pieces[-1])
			pieces.pop()
			name = ' '.join(pieces)
		title = "{0} ({1})".format(name, year).replace('.',' ')
#		print "I think we should call it " + title
#		print "Remaining details are " + m.group(4)
		return title,m.group(4)
	return None,None

##########################################
##########################################
def get_imdb_info(number):
	movie = ia.get_movie(number)
	#print movie['title']
	#print movie['year']
	#print movie['runtimes']
	#print movie['canonical title']
	#print movie['long imdb title']
	#print movie['long imdb canonical title']
	#print movie['smart canonical title']
	title = movie['long imdb title'] if 'long imdb title' in movie else "{0} ({1})".format(movie['title'],movie['year'])
	if isinstance(movie['runtimes'],list):
		movie['runtimes'] = movie['runtimes'][0]
	return title,int(movie['runtimes'])

##########################################
##########################################
# Count the number of filenames which contain things like "blah.cd1.blah"
# This is for detecting movies that have been split into parts (which
# we don't want)
def get_count_of_cds(files):
	regex = '[^a-z0-9]cd[0-9][^a-z0-9]'
	count = 0
	for file in files:
		if re.search(regex, file):
			count += 1
	return count

##########################################
##########################################
# Take a list of filenames and split them
# into ones we want, ones we don't want, and
# ones we're not sure about.
def categorize_files(files):
	movies = []
	subs = []
	dontwant = []
	dontknow = []

	movieendings = '[.](avi|m4v|mkv|mov|mp4|mpeg|mpg|ts)$'
	subendings = '[.](srt)$'
	dontwantendings = '[.](exe|gif|idx|jpg|nfo|nzb|png|sfv|sub|txt)$'

	for fname in files:
		# Gotta do dontwant first, to catch samples with movie endings
		if re.search(dontwantendings,fname.lower()) or re.search('sample',fname.lower()):
			dontwant.append(fname)
		elif re.search(movieendings,fname.lower()):
			movies.append(fname)
		elif re.search(subendings,fname.lower()):
			subs.append(fname)
		else:
			dontknow.append(fname)
	return(movies,subs,dontwant,dontknow)

	
##########################################
##########################################
# Scan through the filenames and see if there are strange things like
# setup.exe or If_you_get_error.txt
def looks_like_trojan(files):
	badfiles = [ 'setupexe', 'ifyougeterrortxt' ]
	bad_count = 0 # How many bad-looking files do we have?
	for filename in files:
		# Lowercase everything, and strip out anything not a-z
		justletters = re.sub('[^a-z]', '', basename(filename).lower())
		if justletters in badfiles:
			bad_count += 1
	return True if bad_count > 0 else False


##########################################
##########################################
def find_imdb_num(files, folders):
	text_endings = [ '.txt', '.nfo' ]
	# Grab any filename and check it for '...(tt#######)"
	m = re.search('\(tt([0-9]{6,})\)', files[0])
	if m != None:
		imdb_num = m.group(1)
		print "Found IMDB number {0}".format(imdb_num)
		return imdb_num

	# Otherwise, search any txt or nfo files for an IMDB URL
	for textfile in files:
		if textfile[-4:] in text_endings:
			with open(textfile) as f:
				lines = f.read()
				m = re.search('imdb.com/title/tt([0-9]{6,})', lines)
				if m != None:
					imdb_num = m.group(1)
					return imdb_num
	return None


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

	title = None
	runtime = None		

#	print "=== Searching for IMDB number ==="
	imdb_num = find_imdb_num(files, folders)
	if imdb_num != None:
		print "Found IMDB number {0}".format(imdb_num)
		title,runtime = get_imdb_info(imdb_num)
		print "Title : {0}  Runtime : {1}".format(title,runtime)

	# If IMDB didn't turn up anything, then we have to guess from
	# filenames
	if title == None:
		runtime = 120 # 2 hours default running time
		for f in files:
			title,details = deduce_title(f)
			# If we finally got a title, then break the loop
			if title != None:
				break

	# Now that we have a running time, we know what the max size should be
	max_size = MAX_RATE * runtime

	# We need to process the filenames to see if there are any
	# foreign language markers (like "FR", "DE", etc.)
	for f in files:
		guessed_title,details = deduce_title(f)
		if details != None:
			dlist = re.split('[. ]',details)
			for detail in dlist:
				if detail.lower() in unwanted_language_codes:
					return False, False, "Found a foreign language flag: {0}".format(detail)

	print "Title = {0}".format(title)
	print "Runtime = {0}".format(runtime)


	# Now, let's figure out what files to copy and which ones to leave
	SOURCE = None

	video_ts_folder = get_video_ts(folders)
	if video_ts_folder != None:
		SOURCE = video_ts_folder
		size = max_size + 1 # Forces a transcode into a file
	else:
		# Search for a single movie file

		movies,subs,dontwant,dontknow = categorize_files(files)
		print "Movies:"
		for f in movies:
			print "	" + f
		print "Subs:"
		for f in subs:
			print "	" + f
		print "We don't want:"
		for f in dontwant:
			print "	" + f
		if len(dontknow) > 0:
			print "We don't know:"
			for f in dontknow:
				print "	" + f

		# This is a list of other files that need to get moved to
		# the destination folder. It is a list of tuples in the 
		# form of [ (oldpath, newname), (oldpath, newname), etc.. ]
		# oldpath = full path to the file to move
		# newname = JUST the name (the folder to move to will be provided)
		move_these = []

		# Process subtitle (SRT) files
		if len(subs) > 0:
			if len(subs) == 1:
				oldname = subs[0]
				newname = title + ".srt"
				move_these.append( (oldname,join(TARGET_FOLDER,newname)) )
			else:
				# There are multiple SRT files. Make sure that they all have language specifiers
				print "Found multiple SRT files. Let's hope that they have language specifiers"
				# Match anything with a dot, then either: 1) two lower-case chars (like 'en' or 'fr') or 
				# 2) an upper- or lower-case char followed by two or more chars (like "English" or "french"
				# and then ".srt"
				regex = '^.*\.([a-z]{2}|[A-Za-z][a-z]{2,})\.srt'
				for sub in subs:
					m = re.search(regex,sub)
					if m != None:
						lang = m.group(1)
						if len(lang) == 2:
							if lang in srt_codes.values():
								pass # Let lang be the two-letter code
							else:
								print "Didn't understand language '{0}'".format(lang)
								continue
						else: # len(lang) > 2
							if lang.lower() in srt_codes.keys():
								oldname = sub
								newname = "{0}.{1}.srt".format(title, lang)
								move_these.append( (oldname,join(TARGET_FOLDER,newname)) )
					else:
						print "Couldn't find a language specifier in {0}".format(sub)

		cd_count = get_count_of_cds(movies)
		if cd_count > 0:
			error_str = "Appears that these are multi-cd parts"
			for f in movies:
				error_str += "\n	" + f
			return False, False, error_str

		if len(movies) > 1:
			error_str = "Too many movie files"
			for f in movies:
				error_str += "\n	" + f
			return False, False, error_str

		if len(movies) < 1:
			return False, False, "No movie file found at {0}".format(folder)

		SOURCE = movies[0]
		size = getsize(SOURCE)

	if title != None:
		# Do we need to resize it?
		if size > max_size:
			print "We need to transcode this"
			if TEST_MODE:
				print "Test mode is on. We would have transcoded '{0}'".format(SOURCE)
			else:	
				SOURCE = transcode(SOURCE, max_size)

		ext = SOURCE.split('.')[-1]
		move_these.append( (SOURCE, join(TARGET_FOLDER,title) + "." + ext) )
		for src,dest in move_these:
			if TEST_MODE:
				print "Test mode is on. We would have moved '{0}' to '{1}'".format(src,dest)
			else:	
				print "moving {0} to {1}".format(src,dest)
				shutil.move(src,dest)
		delete_folder(folder)
		return True, True, "Success"
	return False, False, "Didn't look like we found a title"


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
	soup = bs4.BeautifulSoup(file_contents)
	acts = []
	act_num = 0

	while True:
		found = soup.find(id="search_results")
		if found is None:
			break

		if isinstance(found, bs4.Tag):
			# Remove all of the odd tags that we don't want
			[s.extract() for s in found.findAll('div', attrs={'class' : 'audio-player'}) ]
			[s.extract() for s in found.findAll('span', attrs={'class' : 'tags'}) ]
			[s.extract() for s in found.findAll('ul', attrs={'class' : 'act-contributors'}) ]
			[s.extract() for s in found.findAll('ul', attrs={'class' : 'actions'}) ]

			head = found.find('div', attrs={'class' : 'act-head'}).getText().strip()
			body = found.find('div', attrs={'class' : 'act-body'}).getText().strip()

			act = { 'head' : head, 'body' : body }
			acts.append(act)

			act_num += 1
		else:
			raise Exception("getActs() hit on some HTML which wasn't a tag")

	return acts	

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
<tr style="display:none" id="ihtr5453405">
<td style="background:#ECECD9;" colspan="9">
<table style="width:100%;" cellspacing="0" cellpadding="0" border="0">
<tr>
<td style="border:1px solid #003366">
<iframe style="width:100%; border:0px;" id="ihif5453405"></iframe>
</td>
</tr>
#</table>
#	</td>
#</tr>



#########################################
#########################################
def main():	

	if len(sys.argv) > 7:
		print "Processing args from SABNZBd"
		(folder,nzbname,jobname,reportnum,category,newsgroup,status) = tuple( sys.argv[1:9] )
		print "Processing " + folder
		process(folder,nzbname,jobname,reportnum,category,newsgroup,status)
	else:
		if len(sys.argv) > 1:
			print "Looks like we got a list of saver.* files"
			files = sys.argv[1:]
		else:	
			print "Not enough command lines. Trying to process saver files in /tmp"
			mypath = '/tmp'
			files = [ join(mypath,f) for f in listdir(mypath) if isfile(join(mypath,f)) and f[:5] == "saver" ]

		for filename in files:
			with open(filename) as f:
				print "Processing {0}".format(file)
				(folder,nzbname,jobname,reportnum,category,newsgroup,status) = [ s.strip() for s in f.readlines()[:7] ]
				try:
					success,cleanup,message = process(folder,nzbname,jobname,reportnum,category,newsgroup,status)
					if cleanup:
						if TEST_MODE:
							print "Test mode is on. We would have deleted thedownloaded files" 
						else:	
							print "Removng downloaded files"
							if isfile(filename):
								os.remove(filename)
							if isdir(folder):
								shutil.rmtree(folder)
					print message
				except:
					print "FAILED on {0} because:".format(nzbname)
					print sys.exc_info()[1]
					traceback.print_tb(sys.exc_info()[2])
				print "==============="

if __name__ == "__main__":
	main()
