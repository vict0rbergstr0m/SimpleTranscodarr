Create a simple web app that you can deploy in docker using python and flask (pip package) and probably html. The app should allow you to transcode easier.

done - Choose directory
done - Scan sub folders
done - filters based on regex, or ffprobe (resolution or encoding type), also which supported containers/file endings they should have, somthing like "mkv,avi,ts,mp4...."
done - from the filters fetch a que containing the number off and all files that will be transcoded, (maybe include their original ffprobe infor aswell?)
- Then start transcoding using ffmpeg (!do i need to start it on a different thread to not lock the ui?)
- stop/reset button

- nice to haves
    done - transcoding progress bar, total and per item?
    done - estimated remaining time
    blocked - limit performance, to not stress cpu... (impossible i think)
    done - dynamic page update intervall. only update frequently when stuff is happening.

- bugs
    - if you try to scan the "wrong directory" such as home, it will break. Make sure
    - cant check in on progress while ffmpeg is runnign, ie no time update. i need a seperate thread alive to "read info" from ffmpeg output and supply global data with infomration such as "console output" and total time, and can probably guess time per etc. etc. Learn how yield works

- future features
    - auto scans
        - auto scan intervall
        - auto scan certain libraries/paths and filters
        - remove or add these saved auto scans

    - run schedule (when its allowed to start new transcodings)
        - when a transcoding is done, it checks if its allowed to start the next, if not it waits untill its allowed again. Maybe check every 30 minutes or event when allowed time starts idk