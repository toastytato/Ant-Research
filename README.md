## Table of contents
* [General info](#general-info)
* [Technologies](#technologies)
* [Setup](#setup)
* [Usage](#usage)

## General info
A GUI made to track and log positional data of an ant in a maze using computer vision in Python 
	
## Technologies
Project is created with:
* Python version: 3.7.3
* OpenCV Library version: 4.2.0
	
## Setup
To run this project, download this repository as a ZIP file. Extract the contents and then run main.exe in the dist folder. 

## Usage
The interface has 3 sections: The video frame (top left), the file navigator(bottom left), and the tracker controls(right).

### Video Frame
In the video frame, you can cycle through the different overlays by clicking on the video or click the record button to log the data
#### Video
Click on the video to cycle through the overlays that can be used to visualize how well the tracker is working as well as seeing how well noise is filtered out. The overlays are explained by the following:
* Normal: The raw video feed
* Tracked: Shows the bounding box of the tracked object overlayed on top of the video
* Mask: Shows what the filter sees overlayed on top of the video  
#### Record Button
Press this button to begin recording the video stream as well as log the positional and angular data of the tracked object. Press again to stop logging. A pop-up window will appear to allow you to add a note to the entry and save or discard the entry. 

### File Navigator
In the file navigator, you can review past data entries and view details about them
#### Folder System
Click on the date and time of the entry you want to open up its details
#### Edit Note
To edit the note, select the entry and click 'Edit Details'. The textbox will allow you to edit the notes and clicking the same button will save the edits made
#### Clip 1 and Clip 2
You can view the recorded video for the entry by clicking on these two buttons. Clip 1 will show the video that was on the left, and Clip 2 will show the video that was on the right. They will show up as a pop-up window and close by itself once the video is done. 
#### Export to Excel
Clicking this will export the data recorded to an Excel document saved in the /data folder.  
Right now this will create a new file everytime overwriting the old one. 
#### Delete
Deletes the entry selected

### Tracker Controls
Here you can select the tracker applied to the video on the left. It defaults to the Motion tracker.
#### Motion Tracker
This tracker utilizes motion to determine where the object of interest is. It works best when the camera is locked off and the only thing moving in the frame is the object you want to track. 
* The 'Noise Thresh' slider controls how big the object moving has to be for it to process it. You can use the Mask overlay see what the tracker is trying to lock onto
#### HSV Tracker
This tracker utilizes color to determine where the object of interest it. It works best when the object of interest has high contrast to its background and there is consistent lighting.   
* The 'low_h' and 'high_h' controls the Hue range for the object of interest, which is basically its color. 
* The 'low_s' and 'high_s' controls the Saturation range for the object of interest, which is basically how 'colorful' it is (low saturation like black and white, high saturation is like colored image). 
* The 'low_v' and 'high_v' controls the Value range for the object of interest, which is how dark or bright it is. 




