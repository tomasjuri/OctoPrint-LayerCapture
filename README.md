<p align="center"><img src="https://octoprint.org/assets/img/logo.png" alt="OctoPrint's logo" /></p>

<h1 align="center">OctoPrint</h1>

<p align="center">
  <img src="https://img.shields.io/github/v/release/OctoPrint/OctoPrint?logo=github&logoColor=white" alt="GitHub release"/>
  <img src="https://img.shields.io/pypi/v/OctoPrint?logo=python&logoColor=white" alt="PyPI"/>
  <img src="https://img.shields.io/github/actions/workflow/status/OctoPrint/OctoPrint/build.yml?branch=master" alt="Build status"/>
  <a href="https://community.octoprint.org"><img src="https://img.shields.io/discourse/users?label=forum&logo=discourse&logoColor=white&server=https%3A%2F%2Fcommunity.octoprint.org" alt="Community Forum"/></a>
  <a href="https://discord.octoprint.org"><img src="https://img.shields.io/discord/704958479194128507?label=discord&logo=discord&logoColor=white" alt="Discord"/></a>
  <a href="https://octoprint.org/conduct/"><img src="https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg" alt="Contributor Covenant"/></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-261230" alt="Linting & formatting: ruff"/></a>
  <a href="https://github.com/prettier/prettier"><img src="https://img.shields.io/badge/code_style-prettier-ff69b4.svg" alt="Code style: prettier"/></a>
  <a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"/></a>
</p>

OctoPrint provides a snappy web interface for controlling consumer 3D printers. It is Free Software
and released under the [GNU Affero General Public License V3](https://www.gnu.org/licenses/agpl-3.0.html)[^1].

Its website can be found at [octoprint.org](https://octoprint.org/?utm_source=github&utm_medium=readme).

The community forum is available at [community.octoprint.org](https://community.octoprint.org/?utm_source=github&utm_medium=readme). It also serves as a central knowledge base.

An invite to the Discord server can be found at [discord.octoprint.org](https://discord.octoprint.org).

The FAQ can be accessed by following [faq.octoprint.org](https://faq.octoprint.org/?utm_source=github&utm_medium=readme).

The documentation is located at [docs.octoprint.org](https://docs.octoprint.org).

The official plugin repository can be reached at [plugins.octoprint.org](https://plugins.octoprint.org/?utm_source=github&utm_medium=readme).

**OctoPrint's development wouldn't be possible without the [financial support by its community](https://octoprint.org/support-octoprint/?utm_source=github&utm_medium=readme).
If you enjoy OctoPrint, please consider becoming a regular supporter!**

![Screenshot](https://octoprint.org/assets/img/screenshot-readme.png)

You are currently looking at the source code repository of OctoPrint. If you already installed it
(e.g. by using the Raspberry Pi targeted distribution [OctoPi](https://github.com/guysoft/OctoPi)) and only
want to find out how to use it, [the documentation](https://docs.octoprint.org/) might be of more interest for you. You might also want to subscribe to join
[the community forum at community.octoprint.org](https://community.octoprint.org) where there are other active users who might be
able to help you with any questions you might have.

[^1]: Where another license applies to a specific file or folder, that is noted inside the file itself or a folder README. For licenses of both linked and
      vendored third party dependencies, see also THIRDPARTYLICENSES.md.

## Contributing

Contributions of all kinds are welcome, not only in the form of code but also with regards to the
[official documentation](https://docs.octoprint.org/), debugging help
in the [bug tracker](https://github.com/OctoPrint/OctoPrint/issues), support of other users on
[the community forum at community.octoprint.org](https://community.octoprint.org) or
[the official discord at discord.octoprint.org](https://discord.octoprint.org)
and also [financially](https://octoprint.org/support-octoprint/?utm_source=github&utm_medium=readme).

If you think something is bad about OctoPrint or its documentation the way it is, please help
in any way to make it better instead of just complaining about it -- this is an Open Source Project
after all :)

For information about how to go about submitting bug reports or pull requests, please see the project's
[Contribution Guidelines](https://github.com/OctoPrint/OctoPrint/blob/master/CONTRIBUTING.md).

## Installation

Installation instructions for installing from source for different operating
systems can be found [on the forum](https://community.octoprint.org/tags/c/support/guides/15/setup).

If you want to run OctoPrint on a Raspberry Pi, you really should take a look at [OctoPi](https://github.com/guysoft/OctoPi)
which is a custom SD card image that includes OctoPrint plus dependencies.

The generic steps that should basically be done regardless of operating system
and runtime environment are the following (as *regular
user*, please keep your hands *off* of the `sudo` command here!) - this assumes
you already have Python 3.7+, pip and virtualenv and their dependencies set up on your system:

1. Create a user-owned virtual environment therein: `virtualenv venv`. If you want to specify a specific python
   to use instead of whatever version your system defaults to, you can also explicitly require that via the `--python`
   parameter, e.g. `virtualenv --python=python3 venv`.
2. Install OctoPrint *into that virtual environment*: `./venv/bin/pip install OctoPrint`

You may then start the OctoPrint server via `/path/to/OctoPrint/venv/bin/octoprint`, see [Usage](#usage)
for details.

After installation, please make sure you follow the first-run wizard and set up
access control as necessary.

## Dependencies

OctoPrint depends on a few python modules to do its job. Those are automatically installed when installing
OctoPrint via `pip`.

OctoPrint currently supports Python 3.7, 3.8, 3.9, 3.10, 3.11, 3.12 and 3.13.

Support for Python 3.7 and 3.8 will be dropped with OctoPrint 1.12.0.

## Usage

Running the pip install via

    pip install OctoPrint

installs the `octoprint` script in your Python installation's scripts folder
(which, depending on whether you installed OctoPrint globally or into a virtual env, will be in your `PATH` or not). The
following usage examples assume that the `octoprint` script is on your `PATH`.

You can start the server via

    octoprint serve

By default it binds to all interfaces on port 5000 (so pointing your browser to `http://127.0.0.1:5000`
will do the trick). If you want to change that, use the additional command line parameters `host` and `port`,
which accept the host ip to bind to and the numeric port number respectively. If for example you want the server
to only listen on the local interface on port 8080, the command line would be

    octoprint serve --host=127.0.0.1 --port=8080

Alternatively, the host and port on which to bind can be defined via the config file.

If you want to run OctoPrint as a daemon (only supported on Linux), use

    octoprint daemon {start|stop|restart} [--pid PIDFILE]

If you do not supply a custom pidfile location via `--pid PIDFILE`, it will be created at `/tmp/octoprint.pid`.

You can also specify the config file or the base directory (for basing off the `uploads`, `timelapse` and `logs` folders),
e.g.:

    octoprint serve --config /path/to/another/config.yaml --basedir /path/to/my/basedir

To start OctoPrint in safe mode - which disables all third party plugins that do not come bundled with OctoPrint - use
the ``--safe`` flag:

    octoprint serve --safe

See `octoprint --help` for more information on the available command line parameters.

OctoPrint also ships with a `run` script in its source directory. You can invoke it to start the server. It
takes the same command line arguments as the `octoprint` script.

## Configuration

If not specified via the command line, the config file `config.yaml` for OctoPrint is expected in the settings folder,
which is located at `~/.octoprint` on Linux, at `%APPDATA%/OctoPrint` on Windows and
at `~/Library/Application Support/OctoPrint` on MacOS.

A comprehensive overview of all available configuration settings can be found
[in the docs](https://docs.octoprint.org/en/master/configuration/config_yaml.html).
Please note that the most commonly used configuration settings can also easily
be edited from OctoPrint's settings dialog.

## Special Thanks

Cross-browser testing services are kindly provided by [BrowserStack](https://www.browserstack.com/).

Profiling is done with the help of [PyVmMonitor](https://www.pyvmmonitor.com).

Error tracking is powered and sponsored by [Sentry](https://sentry.io).

# OctoPrint Layer Capture Plugin

An OctoPrint plugin that automatically captures images at specified print layers with configurable grid positions for 3D print monitoring and analysis.

## Features

- 🔄 **Automatic Layer Detection**: Captures images at predefined layer intervals
- 📍 **Configurable Grid Capture**: Takes multiple images in a grid pattern around the print
- 🎯 **Precise Positioning**: Moves print head to exact coordinates for consistent captures
- 🖼️ **Multiple Formats**: Saves images as JPG with comprehensive JSON metadata
- 🛡️ **Safety Features**: Boundary checking and position validation
- 🧪 **Debug Mode**: Fake camera support for testing without hardware
- ⚙️ **Highly Configurable**: Extensive settings for grid spacing, layer intervals, and capture behavior

## Installation

### Manual Installation

1. Clone or download this repository to your local machine
2. Navigate to the plugin directory:
   ```bash
   cd OctoPrint-LayerCapture
   ```

3. Install the plugin using pip in your OctoPrint environment:
   ```bash
   pip install .
   ```

4. Restart OctoPrint

### Plugin Manager Installation (Future)

This plugin will be available through the OctoPrint Plugin Manager in future releases.

## Configuration

After installation, go to **Settings > Plugins > Layer Capture** to configure:

### Grid Configuration
- **Grid Center**: X/Y coordinates of the capture grid center
- **Grid Spacing**: Distance between capture points (default: 40mm)
- **Grid Size**: Number of capture positions (1x1, 3x3, or 5x5)

### Layer Capture Settings
- **Capture Interval**: Capture every N layers (e.g., every 10th layer)
- **Layer Height**: Minimum layer height for calculations

### Camera Settings
- **Fake Camera**: Enable for testing without real camera hardware
- **Capture Delay**: Wait time between movement and capture
- **Return to Origin**: Whether to return print head to original position

### Safety Settings
- **Bed Dimensions**: Width and height of your print bed
- **Boundary Margin**: Safety margin from bed edges
- **Max Z Height**: Maximum Z height limit

## Usage

1. **Configure the plugin** with your printer's bed dimensions and desired capture settings
2. **Start a print** - the plugin will automatically detect when printing begins
3. **Monitor captures** - the plugin will pause the print at specified layers, capture images, and resume automatically
4. **Review results** - captured images and metadata are saved in the uploads/layercapture folder

## File Organization

Captured files are organized as follows:
```
uploads/
└── layercapture/
    ├── layer_0010_pos_00_20241201_143022.jpg
    ├── layer_0010_pos_01_20241201_143025.jpg
    ├── layer_0010_pos_02_20241201_143028.jpg
    ├── layer_0010_metadata_20241201_143030.json
    └── ...
```

## Metadata Format

Each capture session generates a JSON metadata file containing:

```json
{
  "layer": 10,
  "z_height": 2.0,
  "timestamp": 1701436830.123,
  "gcode_file": "test_print.gcode",
  "print_start_time": 1701436000.000,
  "images": [
    {
      "path": "/uploads/layercapture/layer_0010_pos_00_20241201_143022.jpg",
      "position": {"x": 100, "y": 100},
      "index": 0
    }
  ],
  "settings": {
    "grid_spacing": 40,
    "grid_center": {"x": 100, "y": 100},
    "grid_size": 3
  }
}
```

## Development and Testing

### Testing with Fake Camera

Enable "Use Fake Camera" in settings to test the plugin without camera hardware. This will create placeholder text files instead of actual images.

### Virtual Printer Testing

1. Enable OctoPrint's Virtual Printer in Settings > Serial Connection
2. Connect to the virtual printer
3. Upload and print a test GCODE file
4. Monitor the capture behavior in the logs

## Troubleshooting

### Common Issues

**Plugin not appearing in settings:**
- Ensure the plugin is properly installed in the correct Python environment
- Check the OctoPrint logs for any import errors
- Restart OctoPrint completely

**Captures not triggering:**
- Verify Z-change events are being detected
- Check that your layer interval settings are appropriate
- Enable debug logging to see layer detection events

**Grid positions out of bounds:**
- Use the "Show Grid Preview" button to verify positions
- Adjust grid center or reduce grid size/spacing
- Ensure bed dimensions are correctly configured

### Debug Logging

To enable debug logging for the plugin:

1. Go to Settings > Logging
2. Add a new logger: `octoprint.plugins.layercapture`
3. Set level to `DEBUG`
4. Monitor the logs during print capture

## Safety Considerations

⚠️ **Important Safety Notes:**

- Always test with fake camera mode first
- Verify grid positions are within safe bed boundaries
- Monitor first few captures to ensure proper behavior
- Keep print head movement speeds reasonable
- Ensure adequate clearance for all grid positions

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This plugin is licensed under the AGPLv3 License. See [LICENSE](LICENSE) for details.

## Support

- **Issues**: Report bugs and feature requests on [GitHub Issues](https://github.com/example/OctoPrint-LayerCapture/issues)
- **Community**: Join the discussion on the [OctoPrint Community Forum](https://community.octoprint.org)

## Changelog

### v0.1.0 (Initial Release)
- Basic layer capture functionality
- Configurable grid positioning
- Fake camera support for testing
- JSON metadata generation
- Safety boundary checking
- Settings UI with preview functionality
