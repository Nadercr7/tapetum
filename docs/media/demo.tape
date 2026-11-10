# Record with: vhs docs/media/demo.tape (needs tapetum on PATH, vhs and ttyd; run tapetum once first so the demo is quick)
Output docs/media/demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1100
Set Height 560
Set Theme "Dracula"
Set TypingSpeed 40ms
Set Padding 24
Hide
Type "export PS1='$ '"
Enter
Type "clear"
Enter
Sleep 1s
Show
Type "tapetum https://youtu.be/jNQXAC9IVRw --lang en --json | cut -c1-96"
Sleep 500ms
Enter
Sleep 5s
Type "clear"
Enter
Type "head -n 22 ~/.tapetum/youtube-jNQXAC9IVRw/timeline.md"
Sleep 400ms
Enter
Sleep 5s
