# TOOL-E Kiosk GUI

### Installing pyscard on Raspberry Pi OS (Debian/Ubuntu) you can do this once:
```
sudo apt update
sudo apt install \
    build-essential        \
    python3-dev            \   # match whatever Python you’re using (python3.12-dev etc.)
    swig                   \
    libpcsclite-dev        \   # PC/SC headers
    pcscd                  \   # optional, daemon to talk to readers
    libusb-1.0-0-dev       # if you use USB readers

# Then install pyscard in your venv
pip install pyscard
```

### Installing picamera2
```
# make sure the low‑level camera stack is available from the OS
sudo apt update
sudo apt install \
    libcamera-apps libcamera-dev \   # runtime + headers
    libv4l-dev          \             # V4L compatibility (used by picamera2)
    python3-picamera2      # optional – pre‑built wheel for the wrapper

# (in case you also build other extensions such as python-prctl)
sudo apt install build-essential python3-dev \
                 swig libcap-dev

# now install the Python package; if you installed python3-picamera2
# above you can skip this step, otherwise build from pip:
python -m pip install --upgrade pip setuptools wheel
pip install picamera2
```

> **Note:** there is *no* package called `libcamera0` on recent Pi OS versions –
> the library is provided by `libcamera-apps`/`libcamera-dev`.
>
> **If you see a Python error like `No module named libcamera` when launching
> the app, it means the *Python bindings* for libcamera are missing.**
> Those are supplied by the `python3-libcamera` package (or can be pulled in
> automatically by installing `python3-picamera2`), not by `picamera2` itself.
> Install them with:
>
> ```bash
> sudo apt install python3-libcamera
> ```
>
> and make sure the interpreter running the kiosk has access to system
> site‑packages.  If you use a virtualenv, create it with:
>
> ```bash
> python3 -m venv --system-site-packages station-venv
> source station-venv/bin/activate
> pip install -r requirements_pi.txt
> ```
>
> or add `/usr/lib/python3/dist-packages` to the venv’s `PYTHONPATH`.  Once
> the bindings are visible the import error will disappear.

This extra step is often overlooked on a freshly imaged SD card; without
it `picamera2` will fail because it tries to `import libcamera` internally.  
Once the bindings are installed the import error should disappear.