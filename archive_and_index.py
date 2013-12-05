#!/usr/bin/env python
#
# Copyright (C) 2010 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""External archiver for situations where one wants to archive posts in
Mailman's pipermail archive, but also wants to invoke some other process
on the archived message after its URL and/or path are known.

It assumes this is invoked by mm_cfg.py settings like
PUBLIC_EXTERNAL_ARCHIVER = '/path/to/Ext_Arch.py %(listname)s'
PRIVATE_EXTERNAL_ARCHIVER = '/path/to/Ext_Arch.py %(listname)s'

The path in the sys.path.insert() below must be adjusted to the actual path
to Mailman's bin/ directory, or you can simply put this script in Mailman's
bin/ directory and it will work without the sys.path.insert() and of course,
you must add the code you want to the ext_process function.

It archives the file using pipermail archiver but also creates a copy of
each email into separated folder (archive_dir) for later external indexing.

Note the archive_dir must be adjusted to point into folder which ban be
read and modified by external indexing job.

Based on http://www.mail-archive.com/mailman-users@python.org/msg58385.html
Author: Lukas Vlcek (lvlcek@redhat.com), 2011-11-22
"""

import sys
#sys.path.insert(0, '/usr/local/mailman/bin') # path to your mailman dir
sys.path.insert(0, '/usr/lib/mailman/bin')
import paths

import os
import email
import time
import base64

from cStringIO import StringIO

from Mailman import MailList
from Mailman.Archiver import HyperArch
from Mailman.Logging.Syslog import syslog
from Mailman.Logging.Utils import LogStdErr

# For debugging, log stderr to Mailman's 'debug' log
LogStdErr('debug', 'mailmanctl', manual_reprime=0)

# !!!!!! IMPORTANT - adjust if needed !!!!!!
# path to the folder where copy of individual mails will be stored
# do not forget to include a slash at the end of the path
archive_dir='/mnt/nfs.englab.brq.redhat.com/mw-staging/mailman-search-sync/'

def filenameSafeEncode(url):
    """
    Arguments here is the URL to the public mail archive.
    We return file name safe base64 representation of that URL.
    """

    text = base64.b64encode(url).replace('/','_')
    return text

def create_copy(url, content):
    """
    Arguments here are the URL to the just archived message and
    content of original mbox email.
    """

    try:
        filename = filenameSafeEncode(url)
        o = open(archive_dir + filename,'w')
        o.write(content)
        o.close()

    except:
        print "Unexpected error:", sys.exc_info()[0]

    return

def main():
    """This is the mainline.

    It first invokes the pipermail archiver to add the message to the archive,
    then calls the function above to do whatever with the archived message
    after it's URL and path are known.
    """

    listname = sys.argv[1]

    # We must get the list unlocked here because it is already locked in
    # ArchRunner. This is safe because we aren't actually changing our list
    # object. ArchRunner's lock plus pipermail's archive lock will prevent
    # any race conditions.
    mlist = MailList.MailList(listname, lock=False)

    # We need a seekable file for processUnixMailbox()
    f = StringIO(sys.stdin.read())

    # Let's keep copy of original content
    content = f.getvalue()

    h = HyperArch.HyperArchive(mlist)
    # Get the message number for the next message
    sequence = h.sequence
    # and add the message.
    h.processUnixMailbox(f)
    f.close()

    # Get the archive name, etc.
    archive = h.archive
    msgno = '%06d' % sequence
    filename = msgno + '.html'
    h.close()

    url = '%s%s/%s' % (mlist.GetBaseArchiveURL(), archive, filename)

    create_copy(url, content)

if __name__ == '__main__':
    main()
