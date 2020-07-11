import json
from datetime import datetime
from collections import OrderedDict
import os


class DataLog:
    def __init__(self):
        self.id = None
        self.note = ''
        self.url1 = ''
        self.url2 = ''
        self.x = []
        self.y = []
        self.angle = []

        self.entry = {}     # the entry to insert

        self.data = OrderedDict()      # all entries from the json file
        self.json_path = r'..\data\data_logs.json'

        with open(self.json_path, 'r') as read_file:
            try:
                self.data = json.load(read_file)
            except json.decoder.JSONDecodeError:  # if log file is empty, initialize it
                print('Empty data file')
                with open(self.json_path, "w") as write_file:
                    json.dump(self.data, write_file)  # put the empty dictionary into the file

        self.print_data()

    # returns the date and time it was saved to
    def save_entry(self, note, url1, url2):
        self.entry = {}
        self.note = note
        self.url1 = url1
        self.url2 = url2
        now = datetime.now()
        date_key = now.strftime('%m/%d/%Y')
        time_key = now.strftime('%H:%M:%S')
        self.entry['id'] = self.generate_id(date_key)   # self.generate_id(date_key)
        self.entry['notes'] = self.note
        self.entry['x'] = str(self.x)
        self.entry['y'] = str(self.y)
        self.entry['angle'] = str(self.angle)
        self.entry['url1'] = self.url1
        self.entry['url2'] = self.url2
        # reset data arrays after it has been added to entry
        self.x = []
        self.y = []
        self.angle = []
        try:
            self.data[date_key][time_key] = self.entry
        except KeyError:  # if a dictionary hasn't been made inside the date_key entry
            self.data[date_key] = {}
            self.data[date_key][time_key] = self.entry

        with open(self.json_path, "w") as write_file:
            json.dump(self.data, write_file)

        print('entry added')
        self.print_data()

        return date_key, time_key

    def append_values(self, pos, angle):
        self.x.append(pos[0])
        self.y.append(pos[1])
        self.angle.append(angle)

    def print_data(self):
        print(json.dumps(self.data, indent=4))

    def get_dates(self):
        return list(self.data.keys())

    def get_entries(self, date):
        try:
            return list(self.data[date].keys())
        except KeyError:
            return None

    def get_entry(self, date, entry):
        try:
            return self.data[date][entry]
        except KeyError:
            return None

    def generate_id(self, date):
        try:
            last_entry = list(self.data[date].keys())[-1]     # gets the last key
            print('key:', last_entry)
            return self.data[date][last_entry]['id'] + 1  # return last id + 1
        except KeyError:
            return 0        # this is the first entry for today

    def edit_notes(self, note, date, entry):
        self.data[date][entry]['notes'] = note
        with open(self.json_path, "w") as write_file:
            json.dump(self.data, write_file)

    def del_entry(self, date, entry):
        try:
            popped = self.data[date].pop(entry)
        except KeyError:
            print('nothing selected')
            return False

        os.remove(r'..\\clips\\' + popped['url1'] + '.avi')
        os.remove(r'..\\clips\\' + popped['url2'] + '.avi')

        if len(self.data[date]) == 0:
            self.data.pop(date)

        with open(self.json_path, "w") as write_file:
            json.dump(self.data, write_file)
        return True
