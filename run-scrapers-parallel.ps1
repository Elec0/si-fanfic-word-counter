# Run the three scrapers in parallel:
# 1. SI-fanfic-word-count.py -sv
# 2. SI-fanfic-word-count.py -qq
# 3. SI-fanfic-word-count.py -ao3
# Do this by just opening three separate PowerShell windows and running the script in each one.

Invoke-Expression 'cmd /c start pwsh -command { python SI-fanfic-word-count.py -sv;Read-Host -Prompt "Press Enter to exit"}'
Invoke-Expression 'cmd /c start pwsh -command { python SI-fanfic-word-count.py -qq;Read-Host -Prompt "Press Enter to exit"}'
Invoke-Expression 'cmd /c start pwsh -command { python SI-fanfic-word-count.py -ao3;Read-Host -Prompt "Press Enter to exit"}'

