# 100_Tags-

For Education Purposes ⚠️
This is Display of Low level "Reverse Engineering", We tried this experiment of GTA San Andrea's Mobile, personal Save file of the game "GTASAsf*.b". 

Our task was spray all 100 tags in the region of "Los Santos". So, as we can see in the screen-shot that the game is in the Binary Format but It is somewhat readable. The save file is basically a long string of numbers split into labeled "boxes." Each box starts with the literal word "BLOCK" written in the file, followed by a number that says how big that box is. 

First, we had sprayed some tags manually in the game which were exactly 6 then Looked for a looked for a folder whose tab said "100." Out of the whole file, there was exactly one folder like that. Inside it: 100 little switches, almost all set to "off" (the byte 00), except 6 set to "on" (the byte FF). 



Then we used some scripts, written in python. 
1. gtasa_save_core.py — the foundation
Scans the whole file for every spot where the literal text BLOCK appears, reads the 4-byte number right after it (the box's size), and builds a table of every box: where it starts, how big it is, where it ends. Also has the checksum math built in, so every other script can reuse it.

2. verify_block20.py — the wide net
Walks through every BLOCK box in the file and checks the number after each one. Flags any box where that number is exactly 100, since there are 100 tags. This is what found our one candidate box at 0x02A4A0.

3. verify_tag_candidate.py — the close-up
Zooms in on just that one candidate box, prints all 100 bytes with their index numbers, and lists which ones are flagged "done." Read-only — never writes anything.

4. patch_tag_candidate.py — the actual editor
The only script that changes anything. Re-checks the box is really there and the right size, flips all 100 bytes to "done," recalculates the checksum, and saves the result as a new file — leaving the original untouched.

5. gtasa_save_diff.py — comparison tool
A first-draft "compare two saves" script. Lines up two files byte-by-byte and reports where they differ.


I have failed to take screenshot of the exact session where you can see  the "tags block". Here are the two readable screenshots in the binary code which tells us the current status of the game and about the character models such as "Sweet", "Man 1, 2, 3,..... " ( Male models ). Also, the two scripts used in this process. 


This falls into "file format reverse engineering or game save/data reversing" category. 

Thanks :-)
