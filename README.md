# RPstats
Tool for processing readership stats from Real Python.



To run, pull down the repo, install the requirements.txt file with pip, then use:

```bash
$ ./analyze_message.py <input_file>
```

The input file is just the raw text copied from the slackbot reports.  NOTE: I've not extensively tested this.  I suspect it will act goofy if you don't start the file at the top of one of the messages.



