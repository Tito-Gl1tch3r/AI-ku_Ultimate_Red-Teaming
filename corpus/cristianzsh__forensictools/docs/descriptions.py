# -*- coding: utf-8 -*-
"""
Tool descriptions for help.html.

Keys must match the section label in src/sections/<category>/<tool>.nsh.
This script reports any tool that has no entry here.
Run tools/gendocs.py to rebuild.
"""

DESCRIPTIONS = {

    ##### Binary analysis
    'API Monitor': {
        "html": """<p><a href="http://www.rohitab.com/apimonitor" target="_blank">API Monitor</a> is a free software that lets you monitor and control API calls made by applications and services. It's a powerful tool for seeing how applications and services work or for tracking down problems that you have in your own applications.</p>""",
    },
    'capa': {
        "html": """<p><a href="https://github.com/mandiant/capa" target="_blank">capa</a> detects capabilities in executable files. You run it against a PE, ELF, .NET module, shellcode file, or a sandbox report and it tells you what it thinks the program can do. For example, it might suggest that the file is a backdoor, is capable of installing services, or relies on HTTP to communicate.</p>""",
        "examples": [
            'capa.exe suspicious.exe -vv',
            'capa 05be49819139a3fdcdbddbdefd298398779521f3d68daa25275cc77508e42310.json',
        ],
    },
    'CSSC': {
        "html": """<p><a href="https://github.com/cristianzsh/cssc" target="_blank">CSSC</a> is a shellcode encoder and disassembler with a graphical interface, built on Keystone and Capstone.</p>""",
    },
    'Detect It Easy': {
        "html": """<a href="https://github.com/horsicq/Detect-It-Easy" target="_blank">DIE</a> is a cross-platform application; apart from the Windows version there are also versions available for Linux and macOS.""",
    },
    'floss': {
        "html": """<p>The <a href="https://github.com/mandiant/flare-floss" target="_blank">FLARE Obfuscated String Solver (FLOSS, formerly FireEye Labs Obfuscated String Solver)</a> uses advanced static analysis techniques to automatically extract and deobfuscate all strings from malware binaries.</p>""",
        "examples": [
            'floss malware.exe',
            'floss --only stack tight -- suspicious.exe',
        ],
    },
    'Ghidra': {
        "html": """<p><a href="https://github.com/NationalSecurityAgency/ghidra" target="_blank">Ghidra</a> is a software reverse engineering framework, including a disassembler and a decompiler for a wide range of processor architectures.</p>""",
    },
    'ILSpy': {
        "html": """<a href="https://github.com/icsharpcode/ILSpy" target="_blank">ILSpy</a> is the open-source .NET assembly browser and decompiler.""",
    },
    'JD-GUI': {
        "html": """<p><a href="https://java-decompiler.github.io/" target="_blank">JD-GUI</a> is a standalone graphical utility that displays Java source code from <code>.class</code> files, letting you browse reconstructed source and navigate methods and fields.</p>""",
    },
    'Loki': {
        "html": """<p><a href="https://github.com/Neo23x0/Loki-RS" target="_blank">Loki</a> is an IOC scanner. It matches on file names, hashes and YARA rules, and is useful for a quick triage sweep of a suspect host.</p>""",
    },
    'mal_unpack': {
        "html": """<p>The <a href="https://github.com/hasherezade/mal_unpack" target="_blank">mal_unpack</a> deploys a packed malware, waits for it to unpack the payload, dumps the payload, and kills the original process. This unpacker deploys the original malware. Use it only on a Virtual Machine.</p>""",
        "examples": [
            'mal_unpack.exe /exe malware.exe /timeout 2000',
        ],
    },
    'PE-bear': {
        "html": """<p><a href="https://github.com/hasherezade/pe-bear" target="_blank">PE-bear</a> is a multiplatform reversing tool for PE files. Its objective is to deliver fast and flexible &ldquo;first view&rdquo; for malware analysts, stable and capable to handle malformed PE files.</p>""",
    },
    'PEStudio': {
        "html": """<p>The goal of <a href="https://www.winitor.com" target="_blank">pestudio</a> is to spot artifacts of executable files in order to ease and accelerate Malware Initial Assessment.</p>""",
    },
    'PPEE (puppy)': {
        "html": """<p><a href="https://www.mzrst.com" target="_blank">PPEE (puppy)</a> is a Professional PE file Explorer for reversers, malware researchers and those who want to statically inspect PE files in more details.</p>""",
    },
    'pyinstxtractor': {
        "html": """<p><a href="https://github.com/pyinstxtractor/pyinstxtractor-ng" target="_blank">pyinstxtractor</a> extracts the contents of a PyInstaller-generated executable, recovering the bundled <code>.pyc</code> files for further decompilation.</p>""",
        "examples": [
            'pyinstxtractor test.exe',
        ],
    },
    'radare2': {
        "html": """<p><a href="https://github.com/radareorg/radare2" target="_blank">radare2</a> provides a set of libraries, tools and plugins to ease reverse engineering tasks.</p>""",
        "examples": [
            '$ r2 /bin/ls   # open file in read-only',
            '> aaa          # analyse the program (r2 -A)',
            '> afl          # list all functions (try aflt, aflm)',
            '> px 32        # print 32 byte hexdump current block',
            '> s sym.main   # seek to main (using flag name)',
            "> f~foo        # filter flags matching 'foo' (internal |grep)",
            '> iS;is        # list sections and symbols (rabin2 -Ss)',
            '> pdf; agf     # disassembly and ascii-art function graph',
            '> oo+;w hello  # reopen in read-write and write a string',
            '> ?*~...       # interactive filter in all command help',
            '> q            # quit',
        ],
    },
    'scdbg': {
        "html": """<p><a href="https://sandsprite.com/blogs/index.php?uid=7&amp;pid=152" target="_blank">scdbg</a> is a shellcode analysis application built around the libemu emulation library. When run it will display to the user all of the Windows API the shellcode attempts to call.</p>""",
    },
    'UPX': {
        "html": """<p><a href="https://upx.github.io" target="_blank">UPX</a> is a free, secure, portable, extendable, high-performance executable packer for several executable formats.</p>""",
        "examples": [
            'upx -o packed_file.exe original_file.exe',
            'upx -d packed_file.exe',
        ],
    },
    'VT': {
        "html": """<p><a href="https://github.com/VirusTotal/vt-cli" target="_blank">VT</a> is the official VirusTotal command line client. It queries files, hashes, URLs, domains and IP addresses against VirusTotal and can download samples and search Intelligence.</p>""",
        "examples": [
            'vt file 8ac1f5f6ba2ee9b0ba4b1a4bb1e2b6d1',
            'vt url https://example.com',
            "vt search 'type:peexe size:100kb+ positives:5+'",
        ],
    },
    'x64dbg': {
        "html": """<p><a href="https://x64dbg.com" target="_blank">x64dbg</a> is an open-source x64/x32 debugger for windows.</p>""",
    },
    'XVolkolak': {
        "html": """<p>Xvolkolak is an unpacker emulator. Unlike programs of this type, it does not use DebugAPI and other features of the operating system.</p>""",
    },

    ##### Browser utilities
    'BrowsingHistoryView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/browsing_history_view.html" target="_blank">BrowsingHistoryView</a> is a utility that reads the history data of different Web browsers (Mozilla Firefox, Google Chrome, Internet Explorer, Microsoft Edge, Opera) and displays the browsing history of all these Web browsers in one table. The browsing history table includes the following information: Visited URL, Title, Visit Time, Visit Count, Web browser and User Profile. BrowsingHistoryView allows you to watch the browsing history of all user profiles in a running system, as well as to get the browsing history from external hard drive.</p>""",
    },
    'ChromeCacheView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/chrome_cache_view.html" target="_blank">ChromeCacheView</a> is a small utility that reads the cache folder of Google Chrome Web browser, and displays the list of all files currently stored in the cache. For each cache file, the following information is displayed: URL, Content type, File size, Last accessed time, Expiration time, Server name, Server response, and more.</p>""",
    },
    'ChromeCookiesView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/chrome_cookies_view.html" target="_blank">ChromeCookiesView</a> is an alternative to the standard internal cookies viewer of Google Chrome Web browser. It displays the list of all cookies stored by Google Chrome Web browser, and allows you to easily delete unwanted cookies. It also allows you export the cookies into text/csv/html/xml file.</p>""",
    },
    'Hindsight': {
        "html": """<p><a href="https://github.com/RyanDFIR/hindsight" target="_blank">Hindsight</a> parses Chromium-based browser profiles and produces a single timeline of history, downloads, cookies, cache metadata, autofill, local storage and preferences.</p>""",
    },
    'MZCacheView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/mozilla_cache_viewer.html" target="_blank">MZCacheView</a> reads the cache folder of Mozilla Firefox and displays the list of files currently stored there.</p>""",
    },
    'SafariCacheView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/safari_cache_view.html" target="_blank">SafariCacheView</a> reads the <code>Cache.db</code> file of the Safari browser and displays the list of files stored in the cache, along with their URLs and metadata.</p>""",
    },

    ##### Disk forensics
    'bulk_extractor': {
        "html": """<p><a href="https://github.com/simsong/bulk_extractor" target="_blank">bulk_extractor</a> is a high-performance digital forensics exploitation tool. It is a "get evidence" button that rapidly scans any kind of input (disk images, files, directories of files, etc) and extracts structured information such as email addresses, credit card numbers, JPEGs and JSON snippets without parsing the file system or file system structures. The results are stored in text files that are easily inspected, searched, or used as inputs for other forensic processing. bulk_extractor also creates histograms of certain kinds of features that it finds, such as Google search terms and email addresses, as previous research has shown that such histograms are especially useful in investigative and law enforcement applications.</p>""",
        "examples": [
            'bulk_extractor -o bulk-out image.img',
        ],
    },
    'Foremost-NG': {
        "html": """<p><a href="https://github.com/cristianzsh/foremost-ng" target="_blank">Foremost-NG</a> is a file recovery tool that extracts files from disk images or devices by scanning for configurable file headers and footers. It supports common forensic formats (e.g., .dd, Safeback, Encase) and can operate on both image files and live devices.</p>""",
        "examples": [
            'foremost-ng -i disk.img -o /temp/output/carved',
            'foremost-ng -t evtx,elf,exe -i disk.img -o /temp/output/carved',
            'foremost-ng -x -t elf -i memory.dump -o ./carved-files',
        ],
    },
    'OSFMount': {
        "html": """<p><a href="https://www.osforensics.com/tools/mount-disk-images.html" target="_blank">OSFMount</a> allows you to mount local disk image files (bit-for-bit copies of an entire disk or disk partition) in Windows as a physical disk or a logical drive letter. You can then analyze the disk image file with PassMark OSForensics&trade; by using the physical disk name (eg. \\\\.\\PhysicalDrive1) or logical drive letter (eg. Z:). By default, the image files are mounted as read only so that the original image files are not altered.</p>""",
    },
    'PhotoRec / TestDisk': {
        "html": """<p><a href="https://www.cgsecurity.org/wiki/TestDisk_Download" target="_blank">PhotoRec</a> is file data recovery software designed to recover lost files including video, documents and archives from hard disks (Mechanical Hard drives, Solid State Drives...), CD-ROMs, and lost pictures (thus the Photo Recovery name) from digital camera memory. PhotoRec ignores the file system and goes after the underlying data, so it will still work even if your media's file system has been severely damaged or reformatted.</p>

                    <p><a href="https://www.cgsecurity.org/wiki/TestDisk_Download" target="_blank">TestDisk</a> is powerful free data recovery software! It was primarily designed to help recover lost partitions and/or make non-booting disks bootable again when these symptoms are caused by faulty software: certain types of viruses or human error (such as accidentally deleting a Partition Table). Partition table recovery using TestDisk is really easy.</p>""",
    },
    'The Sleuth Kit': {
        "html": """<p><a href="https://www.sleuthkit.org" target="_blank">The Sleuth Kit&reg;</a> is a collection of command line tools and a C library that allows you to analyze disk images and recover files from them. It is used behind the scenes in Autopsy and many other open source and commercial forensics tools.</p>""",
        "examples": [
            'fsstat -i raw evidence.dd',
            'fls -i raw evidence.dd',
            'istat -f ext4 -i raw evidence.dd',
            'mmls evidence.dd',
            'fsstat evidence.dd',
            'img_stat evidence.dd',
        ],
    },

    ##### Windows artifacts
    '$I Parse': {
        "html": """<p><a href="https://df-stream.com/recycle-bin-i-parser/" target="_blank">$I Parse</a> is a tool for parsing $I (index) files from the Recycle Bin of Windows Vista and later.</p>""",
    },
    'AmCache-EvilHunter': {
        "html": """<p><a href="https://github.com/cristianzsh/amcache-evilhunter" target="_blank">AmCache-EvilHunter</a> is a command-line tool to parse and analyze Windows Amcache.hve registry hives, identify evidence of execution, suspicious executables, and integrate VirusTotal/OpenTIP lookups for enhanced threat intelligence.</p>""",
        "examples": [
            'amcache_evilhunter.exe -i Amcache.hve',
            'amcache_evilhunter.exe -i Amcache.hve --start 2021-01-01 --end 2021-12-31 --search notepad',
            'amcache_evilhunter.exe -i Amcache.hve --find-suspicious -v',
            'amcache_evilhunter.exe -i Amcache.hve -v --only-detections --json detections.json',
        ],
    },
    'Amcache.hve parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">AmcacheParser</a> is an Amcache.hve parser with lots of extra features. Handles locked files.</p>""",
        "examples": [
            'AmcacheParser.exe -f "C:\\Temp\\amcache\\AmcacheWin10.hve" --csv C:\\temp',
            'AmcacheParser.exe -f "C:\\Temp\\amcache\\AmcacheWin10.hve" -i on --csv C:\\temp --csvf foo.csv',
            'AmcacheParser.exe -f "C:\\Temp\\amcache\\AmcacheWin10.hve" -w "c:\\temp\\whitelist.txt" --csv C:\\temp',
        ],
    },
    'APT-Hunter': {
        "html": """<p><a href="https://github.com/ahmedkhlief/APT-Hunter" target="_blank">APT-Hunter</a> is a Threat Hunting tool for windows event logs which was made with a purple team mindset to detect APT movements hidden in the sea of windows event logs to decrease the time to uncover suspicious activity. APT-Hunter uses pre-defined detection rules and focuses on statistics to uncover abnormalities which is very effective in compromise assessment.</p>""",
        "examples": [
            'APT-Hunter.exe -p /opt/wineventlogs/ -o Project1 -allreport',
            'APT-Hunter.exe -hunt "psexec" -p /opt/wineventlogs/ -o Project2',
            'APT-Hunter.exe -huntfile "(psexec|psexesvc)" -p /opt/wineventlogs/ -o Project2',
            'APT-Hunter.exe -sigma -rules rules.json -p /opt/wineventlogs/ -o Project2',
        ],
    },
    'BMC-Tools': {
        "html": """<p><a href="https://github.com/ANSSI-FR/bmc-tools" target="_blank">BMC-Tools</a> is an RDP Bitmap Cache parser.</p>""",
    },
    'Chainsaw': {
        "html": """<p><a href="https://github.com/WithSecureLabs/chainsaw" target="_blank">Chainsaw</a> provides a powerful &lsquo;first-response&rsquo; capability to quickly identify threats within Windows forensic artefacts such as Event Logs and the MFT file. Chainsaw offers a generic and fast method of searching through event logs for keywords, and by identifying threats using built-in support for Sigma detection rules, and via custom Chainsaw detection rules.</p>""",
        "examples": [
            'chainsaw hunt EVTX-ATTACK-SAMPLES/ -s sigma/ --mapping mappings/sigma-event-logs-all.yml',
            'chainsaw search mimikatz -i evtx_attack_samples/',
            "chainsaw search -t 'Event.System.EventID: =4104' evtx_attack_samples/",
            'chainsaw search -e "DC[0-9].insecurebank.local" evtx_attack_samples --json',
        ],
    },
    'Event log (evtx) parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">EvtxECmd</a> is an event log (evtx) parser with standardized CSV, XML, and json output! Custom maps, locked file support, and more!</p>""",
        "examples": [
            'EvtxECmd.exe -f "C:\\Temp\\Application.evtx" --csv "c:\\temp\\out" --csvf MyOutputFile.csv',
            'EvtxECmd.exe -f "C:\\Temp\\Application.evtx" --csv "c:\\temp\\out"',
            'EvtxECmd.exe -f "C:\\Temp\\Application.evtx" --json "c:\\temp\\jsonout"',
        ],
    },
    'Hayabusa': {
        "html": """<p><a href="https://github.com/Yamato-Security/hayabusa" target="_blank">Hayabusa</a> is a Windows event log fast forensics timeline generator and threat hunting tool created by the Yamato Security group in Japan.</p>""",
        "examples": [
            'hayabusa.exe search -d ../hayabusa-sample-evtx -k "mimikatz"',
            'hayabusa.exe search -d ../hayabusa-sample-evtx -r "(?:[0-9]{1,3}\\.){3}[0-9]{1,3}"',
            'hayabusa.exe search -d ../hayabusa-sample-evtx -r ".*" -F WorkstationName:"kali"',
        ],
    },
    'Jump List parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">JLECmd</a> is a Jump List parser.</p>""",
        "examples": [
            'JLECmd.exe -f "C:\\Temp\\f01b4d95cf55d32a.customDestinations-ms" --mp',
            'JLECmd.exe -f "C:\\Temp\\f01b4d95cf55d32a.automaticDestinations-ms" --json "D:\\jsonOutput" --jsonpretty',
            'JLECmd.exe -d "C:\\CustomDestinations" --csv "c:\\temp" --html "c:\\temp" -q',
            'JLECmd.exe -d "C:\\Users\\e\\AppData\\Roaming\\Microsoft\\Windows\\Recent" --dt "ddd yyyy MM dd HH:mm:ss.fff"',
        ],
    },
    'JumpListExplorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">JumpListExplorer</a> is a GUI based Jump List viewer.</p>""",
    },
    'LastActivityView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/computer_activity_view.html" target="_blank">LastActivityView</a> is a tool for Windows operating system that collects information from various sources on a running system, and displays a log of actions made by the user and events occurred on this computer. The activity displayed by LastActivityView includes: Running .exe file, Opening open/save dialog-box, Opening file/folder from Explorer or other software, software installation, system shutdown/start, application or system crash, network connection/disconnection and more.</p>""",
    },
    'Lnk file parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">LECmd</a> is a tool for parsing lnk files.</p>""",
        "examples": [
            'LECmd.exe -f "C:\\Temp\\foobar.lnk"',
            'LECmd.exe -f "C:\\Temp\\somelink.lnk" --json "D:\\jsonOutput" --pretty',
            'LECmd.exe -d "C:\\Temp" --csv "c:\\temp" --html c:\\temp --xml c:\\temp\\xml -q',
            'LECmd.exe -f "C:\\Temp\\some other link.lnk" --nid --neb',
            'LECmd.exe -d "C:\\Temp" --all',
        ],
    },
    'LogFileParser': {
        "html": """<p><a href="https://github.com/jschicht/LogFileParser" target="_blank">LogFileParser</a> is a parser for the $LogFile artifact on NTFS.</p>""",
    },
    'MFTECmd': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">MFTECmd</a> is a $MFT, $Boot, $J, $SDS, $I30, and $LogFile parser. Handles locked files.</p>""",
        "examples": [
            'MFTECmd.exe -f "C:\\Temp\\SomeMFT" --csv "c:\\temp\\out" --csvf MyOutputFile.csv',
            'MFTECmd.exe -f "C:\\Temp\\SomeMFT" --csv "c:\\temp\\out"',
            'MFTECmd.exe -f "C:\\Temp\\SomeMFT" --json "c:\\temp\\jsonout"',
            'MFTECmd.exe -f "C:\\Temp\\SomeMFT" --body "c:\\temp\\bout" --bdl c',
            'MFTECmd.exe -f "C:\\Temp\\SomeMFT" --de 5-5',
        ],
    },
    'MFTExplorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">MFTExplorer</a> is a graphical $MFT viewer.</p>""",
    },
    'Prefetch parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">PECmd</a> is a Prefetch parser.</p>""",
        "examples": [
            'PECmd.exe -f "C:\\Temp\\CALC.EXE-3FBEF7FD.pf"',
            'PECmd.exe -f "C:\\Temp\\CALC.EXE-3FBEF7FD.pf" --json "D:\\jsonOutput" --jsonpretty',
            'PECmd.exe -d "C:\\Temp" -k "system32, fonts"',
            'PECmd.exe -d "C:\\Temp" --csv "c:\\temp" --csvf foo.csv --json c:\\temp\\json',
            'PECmd.exe -d "C:\\Windows\\Prefetch"',
        ],
    },
    'Process Microsoft User Access Logs': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">SumECmd</a> processes Microsoft User Access Logs.</p>""",
        "examples": [
            'SumECmd.exe -d "C:\\Temp\\sum" --csv "C:\\Temp\\"',
        ],
    },
    'PyWMIPersistenceFinder': {
        "html": """<p><a href="https://github.com/davidpany/WMI_Forensics/" target="_blank">PyWMIPersistenceFinder</a> parses <code>OBJECTS.DATA</code> to find WMI persistence.</p>""",
        "examples": [
            'PyWMIPersistenceFinder.exe OBJECTS.DATA',
        ],
    },
    'RdpCacheStitcher': {
        "html": """<p><a href="https://github.com/BSI-Bund/RdpCacheStitcher" target="_blank">RdpCacheStitcher</a> reassembles RDP bitmap cache tiles into larger images, making it far easier to interpret what was visible during a remote desktop session. It works on the output of a cache parser such as BMC-Tools.</p>""",
    },
    'RecentFileCacheParser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">RecentFileCache</a> parser.</p>""",
        "examples": [
            'RecentFileCacheParser.exe -f "C:\\Temp\\RecentFileCache.bcf" --csv "c:\\temp"',
            'RecentFileCacheParser.exe -f "C:\\Temp\\RecentFileCache.bcf" --json "D:\\jsonOutput" --jsonpretty',
        ],
    },
    'RECmd': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">RECmd</a> is a powerful command line Registry tool with searching, multi-hive support, plugins, and more.</p>""",
        "examples": [
            'RECmd.exe --f "C:\\Temp\\UsrClass 1.dat" --sk URL --recover false --nl',
            'RECmd.exe --f "D:\\temp\\UsrClass 1.dat" --StartDate "11/13/2014 15:35:01"',
            'RECmd.exe --f "D:\\temp\\UsrClass 1.dat" --RegEx --sv "(App|Display)Name"',
        ],
    },
    'Recycle Bin artifact parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">RBCmd</a> is a Recycle Bin artifact (INFO2/$I) parser.</p>""",
        "examples": [
            'RBCmd.exe -f "C:\\Temp\\INFO2"',
            'RBCmd.exe -f "C:\\Temp\\$I3VPA17" --csv "D:\\csvOutput"',
            'RBCmd.exe -d "C:\\Temp" --csv "c:\\temp"',
        ],
    },
    'RegistryExplorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">Registry Explorer</a> is a registry viewer with searching, multi-hive support, plugins, and more. Handles locked files.</p>""",
    },
    'RegReport': {
        "html": """<p><a href="http://www.gaijin.at/" target="_blank">RegReport</a> produces a readable report of the contents of Windows registry hives, grouping well-known keys into categories such as installed software, autostart entries and hardware.</p>""",
    },
    'Regshot': {
        "html": """<p><a href="https://github.com/Seabreg/Regshot" target="_blank">Regshot</a> takes a snapshot of the registry and the file system, and compares it with a second snapshot taken later. It is the standard way to see exactly what a sample changed during dynamic analysis.</p>""",
    },
    'SBECmd': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">SBECmd</a> is a command line edition for exporting shellbag data.</p>""",
        "examples": [
            'SBECmd.exe -d c:\\temp\\hives --csv c:\\temp\\sbeout',
            'SBECmd.exe -d c:\\temp\\hives --csv c:\\temp\\sbeout --tz "US Eastern Standard Time"',
            'SBECmd.exe -d c:\\temp\\hives --csv c:\\temp\\sbeout --dedupe',
        ],
    },
    'SDBExplorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">SDBExplorer</a> is a Shim database GUI tool.</p>""",
    },
    'ShellBagsExplorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">ShellBagsExplorer</a> is a GUI for browsing shellbags data. Handles locked files.</p>""",
    },
    'ShimCache parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">AppCompatCacheParser</a> is an AppCompatCache aka ShimCache parser.</p>""",
        "examples": [
            'AppCompatCacheParser.exe --csv c:\\temp -t -c 2',
            'AppCompatCacheParser.exe --csv c:\\temp --csvf results.csv',
        ],
    },
    'SRUDB.dat parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">SrumECmd</a> is a SRUM parser.</p>""",
        "examples": [
            'SrumECmd.exe -f "C:\\Temp\\SRUDB.dat" -r "C:\\Temp\\SOFTWARE" --csv "C:\\Temp\\"',
            'SrumECmd.exe -f "C:\\Temp\\SRUDB.dat" --csv "c:\\temp"',
            'SrumECmd.exe -d "C:\\Temp" --csv "c:\\temp"',
        ],
    },
    'SRUM-DUMP': {
        "html": """<p><a href="https://github.com/MarkBaggett/srum-dump" target="_blank">SRUM-DUMP</a> extracts data from the System Resource Utilization Management (SRUM) database and generates an Excel spreadsheet.</p>""",
    },
    'Thumbcache viewer': {
        "html": """<p><a href="https://thumbcacheviewer.github.io" target="_blank">Thumbcache Viewer</a> allows you to extract thumbnail images from the thumbcache_*.db and iconcache_*.db database files found on Windows Vista, Windows 7, Windows 8, Windows 8.1, Windows 10, and Windows 11.</p>""",
    },
    'Triager': {
        "html": """<p><a href="https://github.com/cristianzsh/triager" target="_blank">Triager</a> is a DFIR automation and investigation platform for Windows triage collections. It ingests a collection, runs parsers across the artifacts, and presents the results through a command line interface and a web console.</p>""",
    },
    'uareport': {
        "html": """<p><a href="https://github.com/cristianzsh/uareport" target="_blank">uareport</a> is a command-line tool to parse UserAssist artifacts from Windows registry hives (NTUSER.DAT).</p>""",
        "examples": [
            'uareport.exe -d evidences/Users --csv output.csv',
            'uareport.exe -d /path/to/evidence/Users --user bob --csv bob_userassist.csv',
        ],
    },
    'Windows 10 Timeline database parser': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">WxTCmd</a> is a parser for the Windows 10 Timeline feature database.</p>""",
        "examples": [
            'WxTCmd.exe -f "C:\\Users\\eric\\AppData\\Local\\ConnectedDevicesPlatform\\L.eric\\ActivitiesCache.db" --csv c:\\temp',
        ],
    },
    'Windows File Analyzer': {
        "html": """<p><a href="https://www.mitec.cz/wfa.html" target="_blank">WFA</a> decodes and analyzes some special files used by Windows OS.</p>""",
    },
    'WinPrefetchView': {
        "html": """<p><a href="https://www.nirsoft.net/utils/win_prefetch_view.html" target="_blank">WinPrefetchView</a> is a small utility that reads the Prefetch files stored in your system and displays the information stored in them. By looking in these files, you can learn which files every application is using, and which files are loaded on Windows boot.</p>""",
    },

    ##### macOS artifacts
    'DSStoreParser': {
        "html": """<p><a href="https://github.com/nicoleibrahim/DSStoreParser" target="_blank">DSStoreParser</a> parses <code>.DS_Store</code> files, which record Finder folder settings and can show that a folder or file existed on a system even after deletion.</p>""",
        "examples": [
            'DSStoreParser.exe -s /path/to/mount -o output',
        ],
    },
    'FSEParserV4': {
        "html": """<p><a href="https://github.com/dlcowen/FSEventsParser" target="_blank">FSEParserV4</a> parses macOS File System Events (FSEvents) records, producing a timeline of file system activity from the <code>.fseventsd</code> store.</p>""",
        "examples": [
            'FSEParserV4.exe -s /path/to/fseventsd -o output',
        ],
    },
    'mac_apt': {
        "html": """<p><a href="https://github.com/ydkhatri/mac_apt" target="_blank">mac_apt</a> is a macOS and iOS forensic artifact parsing tool. It processes full disk images (or live machines) and extract data/metadata useful for forensic investigation.</p>""",
    },
    'spotlight_parser': {
        "html": """<p><a href="https://github.com/ydkhatri/spotlight_parser" target="_blank">spotlight_parser</a> reads and extracts data from spotlight databases present on macOS and iOS.</p>""",
        "examples": [
            'spotlight_parser.exe store.db output',
        ],
    },
    'unifiedlog_iterator': {
        "html": """<p><a href="https://github.com/mandiant/macos-UnifiedLogs" target="_blank">unifiedlog_iterator</a> is a simple Rust library that can help parse the macOS Unified Log files.</p>""",
    },

    ##### Mobile forensics
    'ALEAPP': {
        "html": """<p><a href="https://github.com/abrignoni/ALEAPP" target="_blank">ALEAPP</a> is the Android Logs Events And Protobuf Parser. It processes an Android extraction and produces an HTML report covering a wide range of application and system artifacts.</p>""",
    },
    'Android Debug Bridge': {
        "html": """<p><a href="https://developer.android.com/tools/adb" target="_blank">Android Debug Bridge</a> is a versatile command line tool that lets you communicate with an Android device. It supports device actions such as installing and debugging apps, shell access and file transfer.</p>""",
        "examples": [
            'adb devices',
            'adb shell',
            'adb pull /sdcard/DCIM ./DCIM',
            'adb backup -all -f backup.ab',
        ],
    },
    'ApkStudio': {
        "html": """<p><a href="https://github.com/vaibhavpandeyvpz/apkstudio" target="_blank">ApkStudio</a> is an open-source, cross-platform IDE for reverse engineering Android APK files. It decompiles, edits and rebuilds APKs with a graphical interface over apktool.</p>""",
    },
    'iLEAPP': {
        "html": """<p><a href="https://github.com/abrignoni/iLEAPP" target="_blank">iLEAPP</a> processes an iOS extraction and produces an HTML report covering a wide range of application and system artifacts.</p>""",
    },
    'JADX': {
        "html": """<p><a href="https://github.com/skylot/jadx" target="_blank">JADX</a> produces Java source code from Android Dex and APK files. The GUI version lets you browse decompiled code, search across it and follow references.</p>""",
    },
    'scrcpy': {
        "html": """<p><a href="https://github.com/Genymobile/scrcpy" target="_blank">scrcpy</a> displays and controls an Android device connected over USB or TCP/IP.</p>""",
        "examples": [
            'scrcpy',
            'scrcpy --record file.mp4',
            'scrcpy --no-control',
        ],
    },

    ##### Hashing
    'Get-Hashes': {
        "html": """<p>Simple batch script for getting MD5, SHA-1, and SHA-256 hashes.</p>""",
        "examples": [
            'GetHashes file.exe',
        ],
    },
    'HashCalc': {
        "html": """<p><a href="http://www.slavasoft.com/" target="_blank">HashCalc</a> is a free calculator to compute multiple hashes, checksums and HMACs for files, text and hex strings.</p>""",
    },
    'Hasher': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">Hasher</a> is a utility to calculate hashes for files.</p>""",
    },

    ##### Hex editors
    'HxD': {
        "html": """<p><a href="https://mh-nexus.de/en/hxd/" target="_blank">HxD</a> is a carefully designed and fast hex editor which, additionally to raw disk editing and modifying of main memory (RAM), handles files of any size.</p>""",
    },
    'ImHex': {
        "html": """<p><a href="https://github.com/WerWolv/ImHex" target="_blank">ImHex</a> is a hex editor for reverse engineers.</p>""",
    },

    ##### E-mail forensics
    'MailView': {
        "html": """<p><a href="https://www.mitec.cz/mailview.html" target="_blank">MailView</a> is a utility for viewing Outlook Express, Windows Mail/Windows Live Mail and Mozilla Thunderbird message databases as well as single EML files.</p>""",
    },
    'MXRay': {
        "html": """<p><a href="https://github.com/cristianzsh/mxray" target="_blank">MXRay</a> is a graphical e-mail forensics tool. It parses several mailbox and message formats, analyses headers for signs of spoofing, triages attachments, and can enrich findings with VirusTotal lookups.</p>""",
    },

    ##### Memory analysis
    'CobaltStrikeScan': {
        "html": """<p><a href="https://github.com/Apr4h/CobaltStrikeScan" target="_blank">CobaltStrikeScan</a> scans Windows process memory for evidence of DLL injection (classic or reflective injection) and/or performs a YARA scan on the target process' memory for Cobalt Strike v3 and v4 beacon signatures.</p>""",
        "examples": [
            'CobaltStrikeScan.exe -p -d',
        ],
    },
    'MemProcFS': {
        "html": """<p><a href="https://github.com/ufrisk/MemProcFS" target="_blank">MemProcFS</a> is an easy and convenient way of viewing physical memory as files in a virtual file system.</p>""",
        "examples": [
            'memprocfs.exe -device c:\\temp\\win10x64-dump.raw',
            'memprocfs.exe -device c:\\temp\\win10x64-dump.raw -forensic 1 -forensic-yara-rules c:\\yara\\rules\\windows_malware_index.yar',
            'memprocfs.exe -device unknown-x64-dump.raw -pagefile0 pagefile.sys -pagefile1 swapfile.sys',
        ],
    },
    'Vol3': {
        "html": """<p><a href="https://github.com/volatilityfoundation/volatility3" target="_blank">Vol3</a> is the Volatility 3 memory forensics framework. It extracts processes, network connections, injected code, registry hives and much more from a memory image.</p>""",
        "examples": [
            'vol3 -f memory.raw windows.info',
            'vol3 -f memory.raw windows.pslist',
            'vol3 -f memory.raw windows.malfind',
            'vol3 -f memory.raw windows.netscan',
        ],
    },
    'Volatility Workbench': {
        "html": """<p><a href="https://www.osforensics.com/tools/volatility-workbench.html" target="_blank">Volatility Workbench</a> is a free open source tool that provides a graphic user interface for the Volatility memory analysis forensics tool.</p>""",
    },

    ##### Network forensics
    'FakeNet': {
        "html": """<p><a href="https://github.com/mandiant/flare-fakenet-ng" target="_blank">FakeNet</a> is a dynamic network analysis tool that simulates a network so malware running in a sandbox believes it is connected to the internet. It intercepts and logs the traffic, and can respond to common protocols.</p>""",
    },
    'Netcat for Windows': {
        "html": """<p><a href="https://sectools.org/tool/netcat/" target="_blank">nc</a> is a simple utility that reads and writes data across TCP or UDP network connections. It is designed to be a reliable back-end tool to use directly or easily drive by other programs and scripts. At the same time, it is a feature-rich network debugging and exploration tool, since it can create almost any kind of connection you would need, including port binding to accept incoming connections.</p>""",
        "examples": [
            'nc -z -v 10.10.10.10 20-80 # simple port scan',
            'nc -lvp 8080 # listen on port 8080',
        ],
    },
    'NetworkMiner': {
        "html": """<p><a href="https://www.netresec.com/?page=NetworkMiner" target="_blank">NetworkMiner</a> is an open source network forensics tool that extracts artifacts, such as files, images, emails and passwords, from captured network traffic in PCAP files. NetworkMiner can also be used to capture live network traffic by sniffing a network interface. Detailed information about each IP address in the analyzed network traffic is aggregated to a network host inventory, which can be used for passive asset discovery as well as to get an overview of which devices are communicating.</p>""",
    },
    'Wireshark': {
        "html": """<p><a href="https://www.wireshark.org" target="_blank">Wireshark</a> is the world&rsquo;s foremost network protocol analyser. It lets you see what is happening on the network at a microscopic level, with deep inspection of hundreds of protocols and powerful display filters. Live capture requires Npcap, which is installed alongside it.</p>""",
    },

    ##### Password cracking
    'Hash Suite Free': {
        "html": """<p><a href="https://hashsuite.openwall.net" target="_blank">Hash Suite</a> is a Windows program to test security of password hashes.</p>""",
    },
    'hashcat': {
        "html": """<p>hashcat is the world's fastest and most advanced password recovery utility, supporting five unique modes of attack for over 300 highly-optimized hashing algorithms. hashcat currently supports CPUs, GPUs, and other hardware accelerators on Linux, Windows, and macOS, and has facilities to help enable distributed password cracking.</p>""",
        "examples": [
            'hashcat -m 0 -a 0 hash.txt wordlist.txt',
            'hashcat -m 1000 ntlmhash.txt -a 0 rockyou.txt',
        ],
    },
    'Ophcrack': {
        "html": """<p><a href="https://ophcrack.sourceforge.io" target="_blank">Ophcrack</a> is a Windows Password cracker based on Rainbow Tables.</p>""",
    },

    ##### Utilities
    '7-Zip': {
        "html": """<p><a href="https://www.7-zip.org" target="_blank">7-Zip</a> is a file archiver with a high compression ratio.</p>""",
        "examples": [
            '7z x protected.zip',
            '7z a myzip ./MyFolder/*',
        ],
    },
    'bstrings': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">bstrings</a> is an advanced strings search program.</p>""",
        "examples": [
            'bstrings.exe -f "C:\\Temp\\UsrClass 1.dat" --ls URL',
            'bstrings.exe -f "C:\\Temp\\someFile.txt" --lr guid',
            'bstrings.exe -f "C:\\Temp\\aBigFile.bin" --fs c:\\temp\\searchStrings.txt --fr c:\\temp\\searchRegex.txt -s',
            'bstrings.exe -d "C:\\Temp" --mask "*.dll"',
            'bstrings.exe -d "C:\\Temp" --ar "[\\x20-\\x37]"',
            'bstrings.exe -d "C:\\Temp" --cp 10007',
            'bstrings.exe -d "C:\\Temp" --ls test',
            'bstrings.exe -f "C:\\Temp\\someOtherFile.txt" --lr cc --sa',
            'bstrings.exe -f "C:\\Temp\\someOtherFile.txt" --lr cc --sa -m 15 -x 22',
            'bstrings.exe -f "C:\\Temp\\UsrClass 1.dat" --ls mui --sl',
        ],
    },
    'BusyBox for Windows': {
        "html": """<p><a href="https://frippery.org/busybox/" target="_blank">BusyBox</a> is a software suite that provides several Unix utilities in a single executable file.</p>""",
        "examples": [
            'busybox.exe sh',
            'busybox.exe sha1sum file.exe',
            'busybox grep test myfile.txt',
        ],
    },
    'CyberChef': {
        "html": """<p><a href="https://github.com/gchq/CyberChef" target="_blank">CyberChef</a> is a simple, intuitive web app for carrying out all manner of "cyber" operations within a web browser. These operations include simple encoding like XOR and Base64, more complex encryption like AES, DES and Blowfish, creating binary and hexdumps, compression and decompression of data, calculating hashes and checksums, IPv6 and X.509 parsing, changing character encodings, and much more.</p>""",
    },
    'DB Browser for SQLite': {
        "html": """<p><a href="https://sqlitebrowser.org/dl/" target="_blank">DB Browser for SQLite</a> is a high quality, visual, open source tool designed for people who want to create, search, and edit SQLite or SQLCipher database files.</p>""",
    },
    'dd for Windows': {
        "html": """<p><a href="http://www.chrysocome.net/dd" target="_blank">dd</a> command reads one block of input, processes it and writes it into an output file.</p>""",
        "examples": [
            'dd if=\\\\.\\Volume{c18588c0-02e9-11d8-853f-00902758442b} of=c:\\temp\\usb1.img bs=1M',
            'dd if=\\\\?\\Device\\Harddisk1\\Partition0 of=c:\\temp\\usb2.img bs=1M --size --progress',
        ],
    },
    'Dev-C++': {
        "html": """<p><a href="https://sourceforge.net/projects/orwelldevcpp/" target="_blank">Dev-C++</a> is a full-featured C and C++ integrated development environment. The bundled MinGW-w64 toolchain (<code>gcc</code>, <code>g++</code>, <code>gdb</code> and the binutils) is also placed on the PATH.</p>""",
        "examples": [
            'gcc -o test.exe test.c',
            'g++ -O2 -o test.exe test.cpp',
            'gdb test.exe',
        ],
    },
    'ExifTool': {
        "html": """<p><a href="https://exiftool.org" target="_blank">exiftool</a> is a command-line application and Perl library for reading and writing EXIF, GPS, IPTC, XMP, makernotes and other meta information in image, audio and video.</p>""",
        "examples": [
            'exiftool image.jpg',
        ],
    },
    'Firefox': {
        "html": """<p><a href="https://www.mozilla.org/firefox/" target="_blank">Firefox</a> is a free and open-source web browser, included so that HTML reports and locally saved pages can be reviewed without relying on the system browser.</p>""",
    },
    'Java (Temurin JDK 21)': {
        "html": """<p><a href="https://adoptium.net/" target="_blank">Java (Temurin JDK 21)</a> is the Eclipse Temurin build of OpenJDK. Several tools in this toolkit are Java applications and require it; <code>JAVA_HOME</code> is set automatically and <code>java</code> is placed on the PATH.</p>""",
        "examples": [
            'java -version',
            'java -jar tool.jar',
        ],
    },
    'NASM': {
        "html": """<p><a href="https://www.nasm.us/" target="_blank">NASM</a> is the Netwide Assembler, an assembler and disassembler for the x86 architecture. Both <code>nasm</code> and <code>ndisasm</code> are available on the PATH.</p>""",
        "examples": [
            'nasm -f win64 shellcode.asm -o shellcode.obj',
            'ndisasm -b 32 shellcode.bin',
        ],
    },
    'Notepad++': {
        "html": """<p><a href="https://github.com/notepad-plus-plus/notepad-plus-plus" target="_blank">Notepad++</a> is a free source code editor and Notepad replacement that supports several programming languages and natural languages.</p>""",
    },
    'OfficeMalScanner': {
        "html": """<p><a href="http://www.reconstructer.org/code.html" target="_blank">OfficeMalScanner</a> is a MS Office forensic tool to scan for malicious traces, like shellcode heuristics, PE-files or embedded OLE streams. Found files are being extracted to disk. It supports disassembly and hexview as well as an easy brute force mode to detect encrypted files.</p>""",
        "examples": [
            'OfficeMalScanner.exe "C:\\File.xls" scan brute debug',
            'OfficeMalScanner.exe "C:\\File.xls" info',
        ],
    },
    'Process Hacker': {
        "html": """<p><a href="https://sourceforge.net/projects/processhacker/" target="_blank">Process Hacker</a> is a powerful, multi-purpose tool that helps you monitor system resources, debug software and detect malware. It shows detailed process, thread, handle, module and network information for running processes.</p>""",
    },
    'SQLECmd': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">SQLECmd</a> is a tool to find and process SQLite files according to your needs with maps.</p>""",
        "examples": [
            'SQLECmd.exe -f "C:\\Temp\\someFile.db" --csv "c:\\temp\\out"',
            'SQLECmd.exe -d "C:\\Temp\\" --csv "c:\\temp\\out"',
            'SQLECmd.exe -d "C:\\Temp\\" --hunt --csv "c:\\temp\\out"',
        ],
    },
    'SQLite': {
        "html": """<p><a href="https://sqlite.org" target="_blank">SQLite</a> CLI is an application that accepts user input and passes it down into the SQLite library for evaluation.</p>""",
        "examples": [
            '$ sqlite3 ex1',
            'SQLite version 3.36.0 2021-06-18 18:36:39',
            'Enter ".help" for usage hints.',
            'sqlite> create table tbl1(one text, two int);',
            "sqlite> insert into tbl1 values('hello!',10);",
            "sqlite> insert into tbl1 values('goodbye', 20);",
            'sqlite> select * from tbl1;',
            'hello!|10',
            'goodbye|20',
            'sqlite>',
        ],
    },
    'steghide': {
        "html": """<p><a href="https://steghide.sourceforge.net" target="_blank">Steghide</a> is a steganography program that is able to hide data in various kinds of image and audio files.</p>""",
        "examples": [
            'steghide info image.jpg',
            'steghide embed -ef file.txt -cf image.jpg',
            'steghide extract -sf image.jpg',
        ],
    },
    'Timeline Explorer': {
        "html": """<p><a href="https://ericzimmerman.github.io/#!index.md" target="_blank">Timeline Explorer</a> is a tool for viewing CSV and Excel files, as well as applying filters.</p>""",
    },
    'TrID - File Identifier': {
        "html": """<p><a href="https://mark0.net/soft-trid-e.html" target="_blank">TrID</a> is a utility designed to identify file types from their binary signatures. While there are similar utilities with hard coded logic, TrID has no fixed rules. Instead, it's extensible and can be trained to recognize new formats in a fast and automatic way.</p>""",
        "examples": [
            'trid c:\\test\\mydoc.doc',
            'trid c:\\temp\\* -ae',
            'dir d:\\testdrive /s /b | trid -ce -@',
        ],
    },
    'Velociraptor': {
        "html": """<p><a href="https://github.com/Velocidex/velociraptor" target="_blank">Velociraptor</a> is a tool for collecting host based state information using The Velociraptor Query Language (VQL) queries.</p>""",
        "examples": [
            'velociraptor gui',
        ],
    },
    'WinPython': {
        "html": """<p><a href="https://winpython.github.io" target="_blank">WinPython</a> is a free open-source portable distribution of the Python programming language for Windows 10/11 and scientific and educational usage.</p>""",
    },
    'Yara': {
        "html": """<p><a href="https://github.com/VirusTotal/yara" target="_blank">YARA</a> is an open-source tool designed to help malware researchers identify and classify malware samples. It makes it possible to create descriptions (or rules) for malware families based on textual and/or binary patterns. YARA is multi-platform, running on Linux, Windows and Mac OS X. It can be used through its command-line interface or from Python scripts with the YARA-Python extension.</p>""",
        "examples": [
            'yara /foo/bar/rules1 /foo/bar/rules2 .',
            'yara -t Packer -t Compiler /foo/bar/rules bazfile',
            'yara -r /foo',
        ],
    },

    ##### Online search
    'Online search': {
        "html": """<p><strong>Online search</strong> provides right-click shortcuts that submit a file hash or sample to online analysis services, including VirusTotal, Hybrid Analysis, Malware Bazaar and the Kaspersky Threat Intelligence Portal.</p>""",
    },
}

# Scripts under utilities\python\extras_forensictools.
PYTHON_EXTRAS = [
    ('1768.py', """<p><a href="https://github.com/DidierStevens/DidierStevensSuite/blob/master/1768.py" target="_blank">1768.py</a> decrypts and dumps the configuration of Cobalt Strike Windows beacons (PE files), shellcode and memory dumps.</p>""", None),
    ('pdfid.py', """<p><a href="https://blog.didierstevens.com/programs/pdf-tools/" target="_blank">pdfid.py</a> triages a PDF by counting the keywords that matter - <code>/JS</code>, <code>/JavaScript</code>, <code>/OpenAction</code>, <code>/Launch</code>, <code>/EmbeddedFile</code> - so a suspicious document can be spotted before it is opened.</p>""", ['pdfid suspicious.pdf', 'pdfid -e suspicious.pdf']),
    ('pdf-parser.py', """<p><a href="https://blog.didierstevens.com/programs/pdf-tools/" target="_blank">pdf-parser.py</a> walks the objects inside a PDF and can extract and decompress streams, which is the follow-up to a pdfid triage.</p>""", ['pdf-parser -s JavaScript suspicious.pdf', 'pdf-parser -o 12 -f -d out.bin suspicious.pdf']),
    ('oletools', """<p><a href="https://github.com/decalage2/oletools" target="_blank">oletools</a> is a package of Python tools to analyze Microsoft OLE2 files.</p>""", ['oleid test.vb', 'olevba test.vb', 'olevba - deobf - reveal test.vb', 'olevba "test.xlsm"']),
    ('pefile', """<p><a href="https://github.com/erocarrera/pefile" target="_blank">pefile</a> is a multi-platform Python module to parse and work with Portable Executable (PE) files. Most of the information contained in the PE file headers is accessible, as well as all the sections' details and data.</p>""", None),
]
