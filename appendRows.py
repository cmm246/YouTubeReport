#!/usr/bin/python

import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from apiclient import errors

import datetime
import sys
from apiclient.errors import HttpError
from apiclient.discovery import build
from oauth2client.tools import argparser

from myconfig import *


try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
# end if

def get_credentials():
    # Gets valid user credentials from storage.
    #
    # If nothing has been stored, or if the stored credentials are invalid,
    # the OAuth2 flow is completed to obtain the new credentials.
    #
    # Returns:
    #     Credentials, the obtained credential.

    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/sheets.googleapis.com-python.json
    SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
    CLIENT_SECRET_FILE = 'client_secret.json'
    APPLICATION_NAME = 'Google Sheets Append Rows'

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    # end if

    credential_path = os.path.join(credential_dir, 'sheets.googleapis.com-python.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        # end if
        print('Storing credentials to ' + credential_path)
    # end if

    return credentials
# end def

# Globals
credentials = get_credentials()
http = credentials.authorize(httplib2.Http())

def runSheetAppScript(request):
    service = discovery.build('script', 'v1', http=http)

    try:
        response = service.scripts().run(body=request, scriptId=SCRIPT_ID).execute()

        if 'error' in response:
            # The API executed, but the script returned an error.
            # Extract the first (and only) set of error details. The values of
            # this object are the script's 'errorMessage' and 'errorType', and
            # an list of stack trace elements.
            error = response['error']['details'][0]
            print('Script error message: {0}'.format(error['errorMessage']))

            if 'scriptStackTraceElements' in error:
                # There may not be a stacktrace if the script didn't start executing.
                print('Script error stacktrace:')
                for trace in error['scriptStackTraceElements']:
                    print('\t{0}: {1}'.format(trace['function'], trace['lineNumber']))
                # end for
            # end if
        else:
            if 'result' in response['response']:
                return response['response']['result']
            else:
                return None
            # end if
        # end if
    except errors.HttpError as e:
        # The API encountered a problem before the script started executing.
        print(e.content)
    # end try
# end def


def appendVideos(rows):
    request = {"function": "myGetLastRow", "parameters": [SPREADSHEET_ID]}
    lastRow = runSheetAppScript(request)

    request = {"function": "myGetMaxRows", "parameters": [SPREADSHEET_ID]}
    maxRows = runSheetAppScript(request)

    limit = 1001

    if (lastRow + len(rows)) > maxRows:
        request = {"function": "myInsertRowsAfter", "parameters": [SPREADSHEET_ID, limit]}
        runSheetAppScript(request)

    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    rangeName = 'Sheet1!A' + str(lastRow + 1) + ':J'
    columnLength=10
    data = {'values': [row[:columnLength] for row in rows]}
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=rangeName, body=data, valueInputOption='RAW').execute()
# end def


def youtube_search(video_ids):
    # Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
    # tab of
    #   https://cloud.google.com/console
    # Please ensure that you have enabled the YouTube Data API for your project.
    #sudo pip install --upgrade google-api-python-client

    YOUTUBE_API_SERVICE_NAME = 'youtube'
    YOUTUBE_API_VERSION = 'v3'
    
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

    videos = []
    
    dt = datetime.datetime.now()
    dt = datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    # Covert list of ids as string into a list.
    video_ids_list=list(video_ids.split(','))
    # Covert id list into chunks of 50
    l = [video_ids_list[x:x+50] for x in xrange(0, len(video_ids_list), 50)]

    # Process videos 50 at a time
    for i in range(len(l)):
        ids_string = ','.join(l[i]) # Covert chunk of 50 ids back to comma separated string.

        # Call the videos.list method to retrieve location details for each video.
        video_response = youtube.videos().list(
            id=ids_string,
            part='snippet, statistics',
            maxResults=50
        ).execute()

        for video_result in video_response.get('items', []):
            tmp = [
                str(dt), 
                video_result['id'], 
                (video_result['snippet']['publishedAt'])[0:10], 
                video_result['statistics']['viewCount'], 
                video_result['statistics']['likeCount'],
                video_result['statistics']['dislikeCount'],
                video_result['statistics']['favoriteCount'],
                video_result['statistics']['commentCount'],
                'https://www.youtube.com/watch?v=' + video_result['id'],
                video_result['snippet']['channelTitle'],
            ]


            videos.append(tmp)
        # end for
    # end while

    return videos
# end def


if __name__ == '__main__':
    try:
        f = open(SCRIPT_PATH, 'r')
        videoIds = f.read()
        f.close()
        videoIds = videoIds.replace('\n', ',').strip()
        videoIds = videoIds[:-1] # Remove last comma
        appendVideos(youtube_search(videoIds))
    except HttpError, e:
        print('An HTTP error {} occurred:\n{}').format(e.resp.status, e.content)
    # end try
# end main