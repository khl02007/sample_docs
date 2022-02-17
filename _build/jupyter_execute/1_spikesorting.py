#!/usr/bin/env python
# coding: utf-8

# ## Spike Sorting
# 
# **Note: make a copy of this notebook and run the copy to avoid git conflicts in the future**
# 
# This is the second in a multi-part tutorial on the NWB-Datajoint pipeline used in Loren Frank's lab, UCSF. It demonstrates how to run spike sorting and curate units within the pipeline.
# 
# If you have not done [tutorial 0](0_intro.ipynb) yet, make sure to do so before proceeding. It is also recommended that you complete the [datajoint tutorials](https://tutorials.datajoint.io/) before starting this. 
# 
# **Note 2: Make sure you are running this within the nwb_datajoint Conda environment)**

# # Spike Sorting Overview - With associated tables
# #### [Extracting the recording from the NWB file](#section1)<br>
# 1. Specifying your [NWB](#Specifying-your-NWB-filename) file.<br>
# 2. Specifying which electrodes involved in the recording to sort data from. - [`SortGroup`](#SortGroup)<br>
# 3. Specifying the time segment of the recording we want to sort. - [`IntervalList`](#IntervalList), [`SortInterval`](#SortInterval)<br>
# 4. Specifying the parameters to use for filtering the recording. - [`SpikeSortingFilterParameters`](#SpikeSortingFilterParameters)<br>
# 5. Specifying the parameters to apply for artifact detection/removal. -[`SpikeSortingArtifactParameters`](#SpikeSortingArtifactParameters)<br>
# 6. Combining these parameters. - [`SpikeSortingRecordingSelection`](#SpikeSortingRecordingSelection)<br>
# 7. Extracting the recording. - [`SpikeSortingRecording`](#SpikeSortingRecording)<br>
# 8. Add extracted recording to kachery server. - [`SpikeSortingWorkspace`](#SpikeSortingWorkspace)
#     
# #### [Spike sorting the extracted recording](#section2)<br>
# 1. Choose which spike sorting algorithm to use. - [`SpikeSorter`](#SpikeSorter)<br>
# 2. Specify the parameters for that spike sorter to use. - [`SpikeSorterParameters`](#SpikeSorterParameters)<br>
# 3. Combine these parameters. - [`SpikeSortingSelection`](#SpikeSortingSelection)<br>
# 4. Spike sort the extracted recording according to chose parameter set. - [`SpikeSorting`](#SpikeSorting)<br>
# 5. Visualizing the sort using figurl. - [`Visualize`](#Revisiting-SpikeSortingWorkspace)<br>
#     
# 
# <a href='#section1'></a>
# <a href='#section2'></a>

# Let's start by importing tables from nwb_datajoint along with some other useful packages

# In[ ]:


import os
import numpy as np
import datajoint as dj
import nwb_datajoint as nd
# ignore datajoint+jupyter async warnings
import warnings
warnings.simplefilter('ignore', category=DeprecationWarning)
warnings.simplefilter('ignore', category=ResourceWarning)
from nwb_datajoint.common import (SortGroup, SpikeSortingFilterParameters,
                                  SpikeSortingArtifactDetectionParameters,
                                  SpikeSortingRecordingSelection, SpikeSortingRecording, 
                                  SpikeSortingWorkspace, SortingID,
                                  SpikeSorter, SpikeSorterParameters,
                                  SpikeSortingSelection, SpikeSorting, 
                                  SpikeSortingMetricParameters,
                                  AutomaticCurationParameters, AutomaticCurationSelection,
                                  AutomaticCuration, Nwbfile,
                                  CuratedSpikeSortingSelection, CuratedSpikeSorting,
                                  IntervalList, SortInterval,
                                  LabMember, LabTeam, Raw, Session)


# Now let's make sure that you're a part of the LorenLab `LabTeam`, so you'll have the right permissions for this tutorial.<br>Replace `your_name`, `your_email`, and `datajoint_username`, with your information.

# In[ ]:


your_name = 'FirstName LastName'
your_email = 'gmail@gmail.com'
datajoint_username = 'user'


# In[ ]:


lorenlab_team_members = (LabTeam().LabTeamMember() & {'team_name' : 'LorenLab'}).fetch('lab_member_name').tolist()
LabMember.insert_from_name(your_name)
LabMember.LabMemberInfo.insert1([your_name, your_email, datajoint_username], skip_duplicates=True)
LabTeam.LabTeamMember.insert1({'team_name' : 'LorenLab', 
                               'lab_member_name' : your_name}, skip_duplicates=True)


# Now try and use the `fetch` command and the example above to complete the code below and query the `LabTeam` table to double-check that you are a part of the `LorenLab` team.

# In[ ]:


if your_name in (LabTeam._____() & {___:____}).fetch(______).tolist():
    print('You made it in!')


# #### Specifying your NWB filename
# NWB filenames take the form of an animal name plus the date of the recording.<br>For this tutorial, we will use the nwb file `'montague20200802_tutorial_.nwb'`. The animal name is `montague` and the date of the recording is `20200802`, the `tutorial` is unique to this setting :-).<br>We'll first re-insert the NWB file that you deleted at the end of `0_intro`. This file may already be in the table, in which case there will be a warning, that's ok!<br>**Note**: If you're not on the Frank Lab server, this file will be accessible as `montague20200802.nwb` on DANDI through this URL: **insert-url**

# In[ ]:


nd.insert_sessions('montague20200802_tutorial.nwb')
nwb_file_name = 'montague20200802_tutorial_.nwb'


# ### **NOTE**: This is a common file for this tutorial, table entries may change during use if others are also working through.

# <a id='section1'></a>

# ## Extracting the recording from the NWB file

# ### `SortGroup`
# For each NWB file there will be multiple electrodes available to sort spikes from.<br>We commonly sort over multiple electrodes at a time, also referred to as a `SortGroup`.<br>This is accomplished by grouping electrodes according to what tetrode or shank of a probe they were on.<br>**NOTE**: answer 'yes' when prompted

# In[ ]:


# answer 'yes' when prompted
SortGroup().set_group_by_shank(nwb_file_name)


# Each electrode will have an `electrode_id` and be associated with an `electrode_group_name`, which will correspond with a `sort_group_id`. In this case, the data was recorded from a 32 tetrode (128 channel) drive, and thus results in 128 unique `electrode_id`, 32 unique `electrode_group_name`, and 32 unique `sort_group_id`. 

# In[ ]:


SortGroup.SortGroupElectrode & {'nwb_file_name': nwb_file_name}


# ### `IntervalList`
# Next, we make a decision about the time interval for our spike sorting. Let's re-examine `IntervalList`.

# In[ ]:


IntervalList & {'nwb_file_name' : nwb_file_name}


# For our example, let's choose to start with the first run interval (`02_r1`) as our sort interval. We first fetch `valid_times` for this interval.

# In[ ]:


interval_list_name = '02_r1'
interval_list = (IntervalList & {'nwb_file_name' : nwb_file_name,
                            'interval_list_name' : interval_list_name}).fetch1('valid_times')
print(f'IntervalList begins as a {np.round((interval_list[0][1] - interval_list[0][0]) / 60,0):g} min long epoch')


# ### `SortInterval`
# For brevity's sake, we'll select only the first 180 seconds of that 90 minute epoch as our sort interval. To do so, we define our new sort interval as the start time of `interval_list` from the previous cell, plus 180 seconds.

# In[ ]:


sort_interval = interval_list[0]
sort_interval_name = interval_list_name + '_first180'
sort_interval = np.copy(interval_list[0]) 
sort_interval[1] = sort_interval[0]+180


# We can now add this `sort_interval` with the specified `sort_interval_name` `'02_r1_first180'` to the `SortInterval` table. The `SortInterval.insert()` function requires the arguments input as a dictionary with keys `nwb_file_name`, `sort_interval_name`, and `sort_interval`.

# In[ ]:


SortInterval.insert1({'nwb_file_name' : nwb_file_name,
                     'sort_interval_name' : sort_interval_name,
                     'sort_interval' : sort_interval}, skip_duplicates=True)


# Now that we've inserted the entry into `SortInterval` you can see that entry by querying `SortInterval` using the `nwb_file_name` and `sort_interval_name`. 

# In[ ]:


SortInterval & {'nwb_file_name' : nwb_file_name, 'sort_interval_name': sort_interval_name}


# Now using the `.fetch()` command, you can retrieve your user-defined sort interval from the `SortInterval` table.<br>A quick double-check will show that it is indeed a 180 second segment.

# In[ ]:


fetched_sort_interval = (SortInterval & {'nwb_file_name' : nwb_file_name,
                                      'sort_interval_name': sort_interval_name}).fetch1('sort_interval')
print(f'The sort interval goes from {fetched_sort_interval[0]} to {fetched_sort_interval[1]}, which is {(fetched_sort_interval[1] - fetched_sort_interval[0])} seconds. COOL!')


# ### `SpikeSortingFilterParameters`
# Let's first take a look at the `SpikeSortingFilterParameters` table, which contains the parameters used to filter the recorded data in the spike band prior to spike sorting it.

# In[ ]:


SpikeSortingFilterParameters()


# Now let's set the filtering parameters. Here we insert the default parameters, and then fetch the default parameter dictionary.

# In[ ]:


SpikeSortingFilterParameters().insert_default()
filter_param_dict = (SpikeSortingFilterParameters() &
                     {'filter_parameter_set_name': 'default'}).fetch1('filter_parameter_dict')
print(filter_param_dict)


# Lets first adjust the `frequency_min` parameter to 600, which is the preference for hippocampal data. Now we can insert that into `SpikeSortingFilterParameters` as a new set of filtering parameters for hippocampal data, named `'franklab_default_hippocampus'`.

# In[ ]:


filter_param_dict['frequency_min'] = 600
SpikeSortingFilterParameters().insert1({'filter_parameter_set_name': 'franklab_default_hippocampus', 
                                       'filter_parameter_dict' : filter_param_dict}, skip_duplicates=True)


# ### `SpikeSortingArtifactParameters`
# Similarly, we set up the `SpikeSortingArtifactParameters`, which can allow us to remove artifacts from the data.<br>Specifically, we want to target artifact signal that is within the frequency band of our filter (600Hz-6KHz), and thus will not get removed by filtering.<br>For the moment we just set up a `"none"` parameter set, which will do nothing when used.

# In[ ]:


SpikeSortingArtifactDetectionParameters().insert_default()


# #### Setting a key
# Now we set up the parameters of the recording we are interested in, and make a dictionary to hold all these values, which will make querying and inserting into tables all the easier moving forward.<br>We'll assign this to `ssr_key` as these values are relvant to the recording we'll use to spike sort, also referred to as the spike sorting recording **(ssr)** :-)<br>The `sort_group_id` refers back to the `SortGroup` table we populated at the beginning of the tutorial. We'll use `sort_group_id` 10 here. <br>Our `sort_interval_name` is the same as above: `'02_r1_first600'`.<br>Our `filter_param_name` and `artifact_param_name` are the same ones we just inserted into `SpikeSortingFilterParameters` and `SpikeSortingArtifactDetectionParameters`, respectively.<br>The `interval_list` was also set above as `'02_r1'`. Unlike `sort_interval_name`, which reflects our subsection of the recording, we keep `interval_list` unchanged from the original epoch name.

# In[ ]:


key = dict()
key['nwb_file_name'] = nwb_file_name
key['sort_group_id'] = 10
key['sort_interval_name'] = '02_r1_first180'
key['filter_parameter_set_name'] = 'franklab_default_hippocampus'
key['artifact_parameter_name'] = 'none'
key['interval_list_name'] = '02_r1'
key['team_name'] = 'LorenLab'

ssr_key = key


# ### `SpikeSortingRecordingSelection`
# We now insert all of these parameters into the `SpikeSortingRecordingSelection` table, which we will use to specify what time/tetrode/etc of the recording we want to extract.

# In[ ]:


SpikeSortingRecordingSelection.insert1(ssr_key, skip_duplicates=True)
SpikeSortingRecordingSelection() & ssr_key


# ### `SpikeSortingRecording`
# And now we're ready to extract the recording! We use the `.proj()` command to pass along all of the primary keys from the `SpikeSortingRecordingSelection` table to the `SpikeSortingRecording` table, so it knows exactly what to extract.<br>**Note**: This step might take a bit with longer duration sort intervals

# In[ ]:


SpikeSortingRecording.populate([(SpikeSortingRecordingSelection & ssr_key).proj()])


# #### Now we can see our recording in the table. _E x c i t i n g !_

# In[ ]:


SpikeSortingRecording() & ssr_key


# ### `SpikeSortingWorkspace`
# Now we need to populate the `SpikeSortingWorkspace` table to make this recording available via kachery (our server backend).

# In[ ]:


SpikeSortingWorkspace.populate()


# In[ ]:


SpikeSortingWorkspace() & ssr_key


# <a id='section2'></a>

# ## Spike sorting the extracted recording

# ### `SpikeSorter`
# For our example, we will be using `mountainsort4`. There are already some default parameters in the `SpikeSorterParameters` table we'll `fetch`. 

# In[ ]:


SpikeSorter().insert_from_spikeinterface()
SpikeSorterParameters().insert_from_spikeinterface()


# In[ ]:


# Let's look at the default params
sorter_name='mountainsort4'
ms4_default_params = (SpikeSorterParameters & {'sorter_name' : sorter_name,
                                               'spikesorter_parameter_set_name' : 'default'}).fetch1()
print(ms4_default_params)


# Now we can change these default parameters to line up more closely with our preferences. 

# In[ ]:


param_dict = ms4_default_params['parameter_dict']
# Detect downward going spikes (1 is for upward, 0 is for both up and down)
param_dict['detect_sign'] = -1 
# We will sort electrodes together that are within 100 microns of each other
param_dict['adjacency_radius'] = 100
param_dict['curation'] = False
# Turn filter off since we will filter it prior to starting sort
param_dict['filter'] = False
param_dict['freq_min'] = 0
param_dict['freq_max'] = 0
# Turn whiten off since we will whiten it prior to starting sort
param_dict['whiten'] = False
# set num_workers to be the same number as the number of electrodes
param_dict['num_workers'] = 4
param_dict['verbose'] = True
# set clip size as number of samples for 1.33 millisecond based on the sampling rate
param_dict['clip_size'] = np.int(1.33e-3 * (Raw & {'nwb_file_name' : nwb_file_name}).fetch1('sampling_rate'))
param_dict['noise_overlap_threshold'] = 0
param_dict


# ### `SpikeSorterParameters`
# Let's go ahead and insert a new `spikesorter_parameter_set_name` and `parameter_dict` into the `SpikeSorterParameters` table named `franklab_hippocampus_tutorial`. 

# In[ ]:


parameter_set_name = 'franklab_hippocampus_tutorial'


# Now we insert our parameters for use by the spike sorter into `SpikeSorterParameters` and double-check that it made it in to the table. 

# In[ ]:


SpikeSorterParameters.insert1({'sorter_name': sorter_name,
                               'spikesorter_parameter_set_name': parameter_set_name,
                               'parameter_dict': param_dict}, skip_duplicates=True)
# Check that insert was successful
p = (SpikeSorterParameters & {'sorter_name': sorter_name, 'spikesorter_parameter_set_name': parameter_set_name}).fetch1()
p


# ### `SpikeSortingSelection`
# ##### Gearing up to Spike Sort!
# We now collect all the decisions we made up to here and put it into the `SpikeSortingSelection` table, which is specific to this recording and eventual sorting segment.<br>We'll add in a few parameters to our key and call it `ss_key`.<br>(**note**: the spike *sorter* parameters defined above are for the sorter, `mountainsort4` in this case.)

# In[ ]:


key = (SpikeSortingWorkspace & ssr_key).fetch1("KEY")
key['sorter_name'] = sorter_name
key['spikesorter_parameter_set_name'] = parameter_set_name
ss_key = key
SpikeSortingSelection.insert1(ss_key, skip_duplicates=True)
(SpikeSortingSelection & ss_key)


# ### `SpikeSorting`
# Now we can run spike sorting. It's nothing more than populating a table (`SpikeSorting`) based on the entries of `SpikeSortingSelection`.<br>**Note**: This will take a little bit with longer data sets.

# In[ ]:


SpikeSorting.populate([(SpikeSortingSelection & ss_key).proj()])


# #### Check to make sure the table populated

# In[ ]:


SpikeSorting() & ss_key


# ### Revisiting `SpikeSortingWorkspace`
# To peform manual curation, we use the `figurl` interface.<br>`figurl` will load more quickly if we run `SpikeSortingWorkspace().precalculate()` beforehand.

# In[ ]:


SpikeSortingWorkspace().precalculate(ssr_key)


# Here we'll use the sortingview backend to access the figurl *url*. We do this by loading the workspace that we set up while populating `SpikeSortingWorkspace`.<br>This workspace, in tandem with the ids of the spike sorting and recording segment we extracted during this tutorial, will allow us to retrieve the url. We'll also use this opportunity to enable permissions for everyone to curate this sorting. 

# In[ ]:


import sortingview as sv
workspace = sv.load_workspace((SpikeSortingWorkspace() & ssr_key).fetch1('workspace_uri'))
sorting_id = (SortingID() & ssr_key).fetch1('sorting_id')
recording_id = workspace.recording_ids[0]
url = workspace.experimental_spikesortingview(recording_id=recording_id, sorting_id=sorting_id,
                                                  label=workspace.label, include_curation=True)
member_emails = LabMember().LabMemberInfo().fetch('lab_member_name','google_user_name')
member_dict = [email for name, email in zip(member_emails[0], member_emails[1]) if name in lorenlab_team_members]
workspace.set_sorting_curation_authorized_users(sorting_id=sorting_id, user_ids=member_dict)
print(f'{url}')


# ### See 2_curation for the next tutorial
