import json
from datetime import datetime


# TODO: access previous entries in GUI, export to Excel
class DataLog:
    def __init__(self):
        # try to read file
        # if empty, initiate log array
        self.data = {}
        self.entry = {}
        self.note = "yafjals;dfja;ldf"
        self.x = []
        self.y = []
        self.angle = []

        self.json_path = r'..\data\data_logs.json'

        with open(self.json_path, 'r') as read_file:
            try:
                self.data = json.load(read_file)
            except json.decoder.JSONDecodeError:  # if log file is empty, initialize it
                print('Empty data file')
                with open(self.json_path, "w") as write_file:
                    json.dump(self.data, write_file)  # put the empty dictionary into the file

    def save_entry(self, note):
        self.note = note
        now = datetime.now()
        date_key = now.strftime('%m/%d/%Y')
        time_key = now.strftime('%H:%M:%S')
        self.entry = {'notes': self.note,
                      'x': str(self.x),
                      'y': str(self.y),
                      'angle': str(self.angle),
                      'url': 'test'}
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

    def append_values(self, pos, angle):
        self.x.append(pos[0])
        self.y.append(pos[1])
        self.angle.append(angle)

    def print_entry(self):
        print(json.dumps(self.data, indent=4))

    def get_dates(self):
        return list(self.data.keys())

    def get_entries(self, date):
        return list(self.data[date].keys())

    def get_data(self, date, entry):
        return self.data[date][entry]

    def edit_notes(self, note, date, entry):
        self.data[date][entry]['notes'] = note
        with open(self.json_path, "w") as write_file:
            json.dump(self.data, write_file)

    def del_entry(self, date, entry):
        self.data[date].pop(entry)
        if len(self.data[date]) == 0:
            self.data.pop(date)
        with open(self.json_path, "w") as write_file:
            json.dump(self.data, write_file)

