# SI Fanfic Word Count
### [Here is the sheet](https://docs.google.com/spreadsheets/d/127guPMN1mbrYvB-Rggk5-aNa3OiThMhsuslAOfg2wb4/edit?usp=sharing)

This script scrapes the word count of threads on Sufficient Velocity and Questionable Questing, producing a CSV file with the results.  
It reads an index thread and scrapes the word count of all the threads linked in the index thread.  

The two current indexes are both maintained by Nai, who is greatly appreciated:
* https://forums.sufficientvelocity.com/threads/sufficiently-inserted-sv-self-insert-archive-v2-0.41389
* https://forum.questionablequesting.com/threads/questing-for-insertion-qq-self-insert-archive.1094



## Requirements
* Python 3.6 or higher
* `requests` and `beautifulsoup4` Python packages


## Explanation
### Google sheet
The data in this project is processed through a 3-step process, utilizing the following sheets:

* **Raw Data (or Formula):** This sheet contains the raw output from the script, copied into Sheets. Each story is accompanied by a "xx threadmarks, x.xx k words" tag. The Raw Data sheet extracts the numerical values from these tags.
* **Deltas:** The Deltas sheet utilizes the data from the previous scrape to identify newly added stories and calculate the number of words added to each story.
* **Word Counts:** In the Word Counts sheet, the Raw Data is sorted and filtered by word count. Additionally, the sheet highlights newly added stories for easy identification.


## Steps to import
* Copy existing 'Raw Data' sheet, clear `A2:D`
* Select first cell, go File -> Import, select csv file. Pick custom separator `|`, uncheck the box
* Import AO3 data in a copy of the AO3 sheet
* Update the references in 'Merged', 'Deltas', and 'Word counts'