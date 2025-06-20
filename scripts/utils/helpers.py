import datetime
import glob
import os
import re
import subprocess
from configparser import ConfigParser
from itertools import chain

from tzlocal import get_localzone
from suntime import Sun

_settings = None

DB_PATH = os.path.expanduser('~/BirdNET-Pi/scripts/birds.db')
ANALYZING_NOW = os.path.expanduser('~/BirdSongs/StreamData/analyzing_now.txt')
FONT_DIR = os.path.expanduser('~/BirdNET-Pi/homepage/static')


def get_font():
    conf = get_settings()
    if conf['DATABASE_LANG'] == 'ar':
        ret = {'font.family': 'Noto Sans Arabic', 'path': os.path.join(FONT_DIR, 'NotoSansArabic-Regular.ttf')}
    elif conf['DATABASE_LANG'] in ['ja', 'zh']:
        ret = {'font.family': 'Noto Sans JP', 'path': os.path.join(FONT_DIR, 'NotoSansJP-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'ko':
        ret = {'font.family': 'Noto Sans KR', 'path': os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'th':
        ret = {'font.family': 'Noto Sans Thai', 'path': os.path.join(FONT_DIR, 'NotoSansThai-Regular.ttf')}
    else:
        ret = {'font.family': 'Roboto Flex', 'path': os.path.join(FONT_DIR, 'RobotoFlex-Regular.ttf')}
    return ret


class PHPConfigParser(ConfigParser):
    def get(self, section, option, *, raw=False, vars=None, fallback=None):
        value = super().get(section, option, raw=raw, vars=vars, fallback=fallback)
        if raw:
            return value
        else:
            return value.strip('"')


def _load_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    global _settings
    if _settings is None or force_reload:
        with open(settings_path) as f:
            parser = PHPConfigParser(interpolation=None)
            # preserve case
            parser.optionxform = lambda option: option
            lines = chain(("[top]",), f)
            parser.read_file(lines)
            _settings = parser['top']
    return _settings


def get_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    settings = _load_settings(settings_path, force_reload)
    return settings


class Detection:
    def __init__(self, file_date, start_time, stop_time, species, confidence):
        self.start = float(start_time)
        self.stop = float(stop_time)
        self.datetime = file_date + datetime.timedelta(seconds=self.start)
        self.date = self.datetime.strftime("%Y-%m-%d")
        self.time = self.datetime.strftime("%H:%M:%S")
        self.iso8601 = self.datetime.astimezone(get_localzone()).isoformat()
        self.week = self.datetime.isocalendar()[1]
        self.confidence = round(float(confidence), 4)
        self.confidence_pct = round(self.confidence * 100)
        self.species = species
        self.scientific_name = species.split('_')[0]
        self.common_name = species.split('_')[1]
        self.common_name_safe = self.common_name.replace("'", "").replace(" ", "_")
        self.file_name_extr = None


class ParseFileName:
    def __init__(self, file_name):
        self.file_name = file_name
        name = os.path.splitext(os.path.basename(file_name))[0]
        date_created = re.search('^[0-9]+-[0-9]+-[0-9]+', name).group()
        time_created = re.search('[0-9]+:[0-9]+:[0-9]+$', name).group()
        self.file_date = datetime.datetime.strptime(f'{date_created}T{time_created}', "%Y-%m-%dT%H:%M:%S")
        self.root = name

        ident_match = re.search("RTSP_[0-9]+-", file_name)
        self.RTSP_id = ident_match.group() if ident_match is not None else ""

    @property
    def iso8601(self):
        current_iso8601 = self.file_date.astimezone(get_localzone()).isoformat()
        return current_iso8601

    @property
    def week(self):
        week = self.file_date.isocalendar()[1]
        return week


def get_open_files_in_dir(dir_name):
    result = subprocess.run(['lsof', '-w', '-Fn', '+D', f'{dir_name}'], check=False, capture_output=True)
    ret = result.stdout.decode('utf-8')
    err = result.stderr.decode('utf-8')
    if err:
        raise RuntimeError(f'{ret}:\n {err}')
    names = [line.lstrip('n') for line in ret.splitlines() if line.startswith('n')]
    return names


def get_wav_files():
    conf = get_settings()
    files = (glob.glob(os.path.join(conf['RECS_DIR'], '*/*/*.wav')) +
             glob.glob(os.path.join(conf['RECS_DIR'], 'StreamData/*.wav')))
    files.sort()
    files = [os.path.join(conf['RECS_DIR'], file) for file in files]
    rec_dir = os.path.join(conf['RECS_DIR'], 'StreamData')
    open_recs = get_open_files_in_dir(rec_dir)
    files = [file for file in files if file not in open_recs]
    return files

class LocationTime:
    def __init__(self, lat, lon):
        self.timezone = get_localzone()
        self.sun = Sun(lat, lon)
    def is_night(self, compare_time: datetime.datetime):
        local_time = compare_time.astimezone(self.timezone)
        sunrise_time = self.sun.get_local_sunrise_time(local_time.date())
        sunset_time = self.sun.get_local_sunset_time(local_time.date())
        return local_time < sunrise_time or local_time > sunset_time
