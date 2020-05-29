#!/usr/bin/env python3

# Spotify Mute is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation in version 2 of the License.

# Spotify Mute is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License
# along with Spotify Mute. If not, see
# <https://www.gnu.org/licenses/old-licenses>.

# Copyright (c) 2018 Florian Rademacher <florian.rademacher@fh-dortmund.de>

import argparse
import configparser
import logging
import os.path
import re
import subprocess
import sys
import time

from abc import ABC, abstractmethod
from gi.repository import GLib
from pydbus import SessionBus

_NAME = 'Spotify Mute'
_VERSION = '0.5'

class CommandlineInterface:
    def __init__(self):
        self._argument_parser = argparse.ArgumentParser(
            description='Mute Spotify advertisements')
        self._argument_parser.add_argument('-c', '--config',
            dest='configuration_file', help='Configuration file path')
        self._argument_parser.add_argument('-v', '--version',
            action='store_true', dest='has_version',
            help='Print version information')

    def parse_arguments(self):
        self._parsed_arguments = self._argument_parser.parse_args()

    def get_configuration_file(self):
        try:
            return self._parsed_arguments.configuration_file
        except AttributeError:
            return None

    def has_version(self):
        return self._parsed_arguments.has_version

class Configuration:
    MAIN_CONFIG_SECTION = 'SPOTIFY_MUTE'
    MUTIFY_MODE = 'MUTIFY'
    _VALID_MODES = [MUTIFY_MODE]

    _DEFAULT_MODE = MUTIFY_MODE
    _DEFAULT_SHOW_NOTIFICATION = True
    _DEFAULT_WAIT_BEFORE_UNMUTE = 0
    _DEFAULT_VALUES = {
        'Mode' : _DEFAULT_MODE,
        'ShowNotification' : _DEFAULT_SHOW_NOTIFICATION,
        'WaitBeforeUnmute' : _DEFAULT_WAIT_BEFORE_UNMUTE
    }

    _MAIN_CONFIG_SECTION_VALID_ENTRIES = [
        'Mode', 
        'ShowNotification', 
        'WaitBeforeUnmute'
    ]
    _MUTIFY_MODE_VALID_ENTRIES = [
        'ShowNotification',
        'WaitBeforeUnmute'
    ]
    _VALID_CONFIGURATION = {
        MAIN_CONFIG_SECTION : _MAIN_CONFIG_SECTION_VALID_ENTRIES,
        MUTIFY_MODE : _MUTIFY_MODE_VALID_ENTRIES
    }

    _parsing_successful = False

    def __init__(self):
        self._configuration_file = None

        self._main_config_entries = {}
        self._mutify_config_entries = {}

        self.set_missing_values_default()

    def __getitem__(self, items):
        if not items:
            return None

        if isinstance(items, str):
            return self._get_configuration_item_str(items)
        elif isinstance(items, tuple):
            return self._get_configuration_item_tuple(items)
        else:
            return None

    def parse_configuration(self, configuration_file):
        self._parsing_successful = False

        # Check if configuration file exists (otherwise open() raises a
        # FileNotFound exception)
        fd = open(configuration_file, 'r')
        fd.close()

        self._parsed_configuration = configparser.ConfigParser()
        # Don't lowercase option names
        self._parsed_configuration.optionxform = lambda option: option
        self._parsed_configuration.read(configuration_file)

        self._validate_config_sections()
        self._validate_config_entries()
        self._validate_mode()
        self._validate_wait_before_unmute()

        self._configuration_file = configuration_file
        self._parsing_successful = True

        self._build_config_entries_dict(self.MAIN_CONFIG_SECTION)
        self._build_config_entries_dict(self.MUTIFY_MODE)

    def get_configuration_file(self):
        return self._configuration_file

    def set_missing_values_default(self):
        for configurationKey in self._DEFAULT_VALUES:
            if not configurationKey in self._main_config_entries:
                defaultValue = self._DEFAULT_VALUES[configurationKey]
                self._main_config_entries[configurationKey] = defaultValue

    def get_effective_configuration_values(self):
        effectiveConfiguration = {}

        configuredMode = self._main_config_entries['Mode']
        modeConfiguration = self._get_configuration_dict(configuredMode)
        for key, value in modeConfiguration.items():
            effectiveConfiguration[key] = value

        for key in self._main_config_entries:
            if not key in effectiveConfiguration:
                effectiveConfiguration[key] = self._main_config_entries[key]

        return effectiveConfiguration

    def _build_config_entries_dict(self, configuration_section):
        if not configuration_section in self._parsed_configuration.sections():
            return

        dictionary = self._get_configuration_dict(configuration_section)
        for entry in self._parsed_configuration[configuration_section]:
            dictionary[entry] = self._get_entry_from_parsed_configuration(
                configuration_section, entry)
        
    def _get_configuration_dict(self, configuration_section):
        if configuration_section not in self._VALID_CONFIGURATION:
            raise NotImplementedError('Configuration dictionary not ' \
                'implemented for section "%s"' % configuration_section)

        if configuration_section == self.MAIN_CONFIG_SECTION:
            return self._main_config_entries
        elif configuration_section == self.MUTIFY_MODE:
            return self._mutify_config_entries

    def _get_entry_from_parsed_configuration(self, section, entry_name, 
        raw=False):
        if not self._parsed_configuration or \
            section not in self._parsed_configuration or \
            entry_name not in self._parsed_configuration[section]:
            return None

        if not raw and entry_name == 'ShowNotification':
            showNotification = self._parsed_configuration[section][entry_name]
            return showNotification.lower() != 'false'

        if not raw and entry_name == 'WaitBeforeUnmute':
            waitBeforeUnmute = self._parsed_configuration[section][entry_name]
            return float(waitBeforeUnmute)

        return self._parsed_configuration[section][entry_name]

    def _get_configuration_item_tuple(self, items):
        resultConfigEntries = {}

        for item in items:
            configurationEntriesForItem = \
                self._get_configuration_item_str(item)
            resultConfigEntries[item] = configurationEntriesForItem

        return resultConfigEntries

    def _get_configuration_item_str(self, string):
        if string in self._VALID_MODES or  \
            string == self.MAIN_CONFIG_SECTION:
            return self._get_configuration_dict(string)

        if 'Mode' in self._main_config_entries:
            configuredMode = self._main_config_entries['Mode']
            modeConfiguration = self._get_configuration_dict(configuredMode)
            if string in modeConfiguration:
                return modeConfiguration[string]

        if string in self._main_config_entries:
            return self._main_config_entries[string]

        raise KeyError(string)

    def _validate_config_sections(self):
        for section in self._parsed_configuration.sections():
            if section not in self._VALID_CONFIGURATION:
                raise self.InvalidConfigurationSectionError(section)

    def _validate_config_entries(self):
        for section in self._parsed_configuration.sections():
            for entry in self._parsed_configuration[section]:
                if entry not in self._VALID_CONFIGURATION[section]:
                    raise self.InvalidConfigurationEntryError(section, entry)

    def _validate_mode(self):
        configuredMode = \
            self._get_entry_from_parsed_configuration(self.MAIN_CONFIG_SECTION,
                'Mode')

        if configuredMode not in self._VALID_MODES:
            raise self.InvalidConfigurationEntryValueError('Mode',
                configuredMode, self._VALID_MODES)

    def _validate_wait_before_unmute(self):
        configuredMode = \
            self._get_entry_from_parsed_configuration(self.MAIN_CONFIG_SECTION,
                'Mode')
        configuredWaitTime = \
            self._get_entry_from_parsed_configuration(configuredMode,
                'WaitBeforeUnmute', True)

        if not configuredWaitTime:
            configuredWaitTime = \
                self._get_entry_from_parsed_configuration(
                    self.MAIN_CONFIG_SECTION, 'WaitBeforeUnmute', True)

        if configuredWaitTime:
            try:
                configuredWaitTimeFloat = float(configuredWaitTime)
                if configuredWaitTimeFloat < 0:
                    raise self.InvalidConfigurationEntryValueError(
                        'WaitBeforeUnmute', configuredWaitTime,
                        ['greater or equal zero'])
            except ValueError:
                raise self.InvalidConfigurationEntryValueError(
                    'WaitBeforeUnmute', configuredWaitTime, ['of type float'])

    def __str__(self):
        if not self._parsing_successful:
            return ''

        configurationKeyTuple = tuple([self.MAIN_CONFIG_SECTION]) \
            + tuple(self._VALID_MODES)
        configEntries = \
            self._get_configuration_item_tuple(configurationKeyTuple)
        return str(configEntries)

    class InvalidConfigurationEntryValueError(Exception):
        def __init__ (self, entry, value, valid_values=[]):
            self.entry = entry
            self.value = value
            self.valid_values = valid_values

        def __str__(self):
            validValuesHint = ''
            if self.valid_values:
                validValuesCommaSeparated = \
                    ', '.join(map(str, self.valid_values))
                validValuesHint = 'Valid values would be: %s.' % \
                    validValuesCommaSeparated

            return 'Invalid configuration value detected for entry "%s": ' \
                '%s. %s' % (self.entry, self.value, validValuesHint)

    class MissingConfigurationEntryValueError(Exception):
        def __init__(self, entry, additional_explanation=''):
            self.entry = entry
            self.additional_explanation = additional_explanation

        def __str__(self):
            message = 'Missing value for configuration entry "%s". ' % \
                self.entry
            return message + self.additional_explanation

    class InvalidConfigurationSectionError(Exception):
        def __init__(self, section, additional_explanation=''):
            self.section = section
            self.additional_explanation = additional_explanation

        def __str__(self):
            message = 'Invalid configuration section "%s". ' % self.section
            return message + self.additional_explanation

    class InvalidConfigurationEntryError(Exception):
        def __init__(self, section, entry, additional_explanation=''):
            self.section = section
            self.entry = entry
            self.additional_explanation = additional_explanation

        def __str__(self):
            message = 'Invalid configuration entry "%s" in section "%s". ' % \
                (self.entry, self.section)
            return message + self.additional_explanation

class Util(ABC):
    @staticmethod
    def show_notification(summary, body, timeout):
        sessionBus = SessionBus()
        notifications = sessionBus.get('.Notifications')
        notifications.Notify(Util.application_name(), 0, 'dialog-information',
            summary, body, [], {}, timeout)

    @staticmethod
    def application_name():
        scriptFileParts = os.path.splitext(sys.argv[0])

        if scriptFileParts:
            return os.path.basename(scriptFileParts[0])
        else:
            return 'spotify_mute'

class MuteModeStrategy(ABC):
    _DBUS_BASE_INTERFACE = 'org.mpris.MediaPlayer2'
    _DBUS_PLAYER_INTERFACE = _DBUS_BASE_INTERFACE + '.Player'
    _DBUS_PLAYER_PATH = '/org/mpris/MediaPlayer2'
    _DBUS_SPOTIFY_NAME = _DBUS_BASE_INTERFACE + '.spotify'

    def __init__(self, configuration):
        self._previous_track_id = None

        self._configuration = configuration
        self._show_mute_notification = configuration['ShowNotification']
        self._wait_before_unmute = configuration['WaitBeforeUnmute']

    def ad_start_before(self):
        pass

    @abstractmethod
    def ad_start(self):
        pass

    def ad_start_after(self):
        if self._show_mute_notification:
            Util.show_notification('Sound muted', 'Advertisement detected, ' \
                'sound is now muted', 2000)
            # Show mute notification once per advertisement block
            self._show_mute_notification = False

    def ad_stop_before(self):
        if self._wait_before_unmute:
            time.sleep(self._wait_before_unmute)

    @abstractmethod
    def ad_stop(self):
        pass

    def ad_stop_after(self):
        self._show_mute_notification = self._configuration['ShowNotification']

    def spotify_connect(self):
        sessionBus = SessionBus()
        playerProxy = sessionBus.get(self._DBUS_SPOTIFY_NAME, 
            self._DBUS_PLAYER_PATH)
        playerProxy.PropertiesChanged.connect(
            self._spotify_played_title_changed)

    def _spotify_played_title_changed(self, interface_name, changed_properties,
        invalidated_properties):
        if interface_name != self._DBUS_PLAYER_INTERFACE:
            return
    
        if not 'PlaybackStatus' in changed_properties or \
            not 'Metadata' in changed_properties:
            return

        if changed_properties['PlaybackStatus'] != 'Playing':
            return

        if not 'mpris:trackid' in changed_properties['Metadata']:
            return

        currentTrackId = changed_properties['Metadata']['mpris:trackid']
        if not isinstance(currentTrackId, str):
            return

        if self._previous_track_id == currentTrackId:
            return
        else:
            self._previous_track_id = currentTrackId

        if currentTrackId.startswith('spotify:ad'):
            self.ad_start_before()
            self.ad_start()
            self.ad_start_after()
        else:
            self.ad_stop_before()
            self.ad_stop()
            self.ad_stop_after()

class MutifyMode(MuteModeStrategy):
    _MUTE_MASTER_COMMAND = 'amixer -qD pulse sset Master mute'
    _UNMUTE_MASTER_COMMAND = 'amixer -qD pulse sset Master unmute'

    def __init__(self, configuration):
        super().__init__(configuration)

    def ad_start(self):
        self._mute_master()

    def ad_stop(self):
        self._unmute_master()

    def _mute_master(self):
        subprocess.Popen(self._MUTE_MASTER_COMMAND.split())

    def _unmute_master(self):
        subprocess.Popen(self._UNMUTE_MASTER_COMMAND.split())

def _critical_error(message):
    logging.getLogger().error(message + ' Exiting.')
    sys.exit(4)

def _debug(message):
    logging.getLogger().debug(message)

def _print_effective_configuration_values(configuration):
    effectiveConfiguration = configuration.get_effective_configuration_values()
    lengthOfLongestKey = max(map(
        lambda s: len(s), effectiveConfiguration.keys()
    ))
    formatString = '  %-' + str(lengthOfLongestKey) + 's = %s'

    logging.getLogger().info('Current configuration is:')
    for key in sorted(effectiveConfiguration):
        value = effectiveConfiguration[key]
        logging.getLogger().info(formatString % (key, value))

def _print_version():
    logging.getLogger().info('This is %s version %s.' % (_NAME, _VERSION))

def _die_if_spotify_is_not_running():
    for runningProcess in psutil.process_iter(['name']):
        if runningProcess.name() == 'spotify':
            return True

    sys.exit(0)

if __name__ == '__main__':
    logging.basicConfig(format=None, level=logging.INFO)

    commandline = CommandlineInterface()
    commandline.parse_arguments()

    if commandline.has_version():
        _print_version()
        sys.exit(0)

    configurationFile = commandline.get_configuration_file()    
    configuration = Configuration()
    if configurationFile:
        try:
            configuration.parse_configuration(configurationFile)
        except FileNotFoundError:
            logging.getLogger().warning('Configuration file "%s" not found. ' \
                'Using default configuration.' % \
                commandline.get_configuration_file())
        except (Configuration.InvalidConfigurationEntryValueError,
            Configuration.MissingConfigurationEntryValueError,
            Configuration.InvalidConfigurationSectionError,
            Configuration.InvalidConfigurationEntryError) as err:
            _critical_error(str(err))
        except configparser.Error as err:
            _critical_error('Error while parsing configuration: %s.' %
                err.message)
    else:
        logging.getLogger().warning('No configuration file specified. Using ' \
            'default configuration.')

    _debug(configuration)

    _print_version()
    _print_effective_configuration_values(configuration)

    muteMode = configuration['Mode']
    muteStrategy = None
    if muteMode == Configuration.MUTIFY_MODE:
        muteStrategy = MutifyMode(configuration)

    try:
        muteStrategy.spotify_connect()
    except GLib.Error as err:
        _critical_error('Couldn\'t connect to Spotify service. Is Spotify ' \
            'running? (Detailed error was "%s").' % err)

    GLib.timeout_add(3000, _die_if_spotify_is_not_running)

    eventLoop = GLib.MainLoop()
    eventLoop.run()