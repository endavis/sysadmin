"""A module to run commands through the ONTAP CLI."""

import logging
import json

import paramiko

from netapp_ontap import HostConnection  # pyright: ignore[reportPrivateImportUsage]
from netapp_ontap.resources import CLI

cmd_keys = {}
cmd_keys["volume show"] = "Volume Name"
cmd_keys["vol show"] = "Volume Name"


class CLICommandError(Exception):
    """Exception raised for CLI Commands.

    Attributes:
        message -- The custom error string to show with the exception

    """

    def __init__(self, message):
        """Initialize the class.

        :param message: The custom error string to sshow with the exception
        """
        self.message = message
        super().__init__(self.message)


class ONTAPCLI:
    """Class to run commands through the ONTAP CLI."""

    def __init__(self, name, host_or_ip, username, password):
        """Initialize the class.

        :param name: the name of the host
        :param host_or_ip: the ip or hostname to connect to
        :param username: the username
        :param password: the password
        """
        self.name = name
        self.host = host_or_ip
        self.username = username
        self.password = password

        self.ssh: paramiko.SSHClient = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.cli = self.ssh

        self.lines_to_skip = ["Unsuccessful login attempts since last login"]
        self.lines_to_skip.append("Last login time:")
        self.lines_to_skip.append("Your privilege has changed since last login.")
        self.lines_to_skip.append("This is your first recorded login.")

        # self.username = username
        # self.pw = pw
        # self.pkey_filename = keyfile
        # self.pkey_pw = keyfile_pw

        self.pkey = None
        # if self.pkey_filename:
        #     self.pkey = paramiko.RSAKey.from_private_key_file(self.pkey_filename,
        #                                   password=self.pkey_pw)

    def connect(self):
        """Connect to the server."""
        if (
            not self.ssh.get_transport()
            or not self.ssh.get_transport().is_active()  # pyright: ignore[reportOptionalMemberAccess]
        ):
            logging.debug("Connect: creating connection")
            if self.pkey:
                self.ssh.connect(self.host, username=self.username, pkey=self.pkey)
            else:
                self.ssh.connect(
                    self.host, username=self.username, password=self.password
                )
            self.ssh.get_transport().set_keepalive(  # pyright: ignore[reportOptionalMemberAccess]
                5
            )

    def run_command_and_parse(
        self, cmd, arguments="", respondto=" {y|n}:", response="y\n"
    ):
        """Run and parse a command.

        :param cmd: the command
        :param arguments: the arguments to the command
        :param respondto: prompt to respond to
        :param response: the string to respond with
        """
        output = self.run_command(cmd, arguments, respondto, response)

        primary_key = None

        if cmd in cmd_keys:
            primary_key = cmd_keys[cmd]

        return self.parse_generic_output(output, primary_key=primary_key)

    def run_a_show_command_and_parse_seperator(
        self, cmd, arguments="", respondto=" {y|n}:", response="y\n"
    ):
        """Parse a show command with separators.

        :param cmd: the command
        :param arguments: the arguments to the command
        :param respondto: prompt to respond to
        :param response: the string to respond with
        """
        cmd = (
            f"set d -confirmations off;set -showallfields true"
            f';set -showseparator ",";{cmd}'
        )

        output = self.run_command(cmd, arguments, respondto, response)

        if not output:
            logging.info(f"{cmd} returned no output")
            return [], {}

        headers = output[0].split(",")
        if "" in headers:
            del headers[headers.index("")]
        del output[0]

        descriptions = output[0].split(",")
        if "" in descriptions:
            del descriptions[descriptions.index("")]
        descriptions_dict = dict(zip(headers, descriptions))
        del output[0]

        data = []
        for line in output:
            tdata = line.split(",")
            datadict = dict(zip(headers, tdata))
            if "" in datadict:
                del datadict[""]

            data.append(datadict)

        return data, descriptions_dict

    def run_command(self, cmd, arguments="", respondto=" {y|n}:", response="y\n"):
        """Run a command through the CLI and return the output.

        :param cmd: the command
        :param arguments: the arguments to the command
        :param respondto: prompt to respond to
        :param response: the string to respond with
        """
        output = []

        self.connect()
        # print("command: %s" % cmd)
        logging.info(f"host {self.name}:{self.host} - running '{cmd}'")

        stdin, stdout, stderr = self.cli.exec_command(f"{cmd} {arguments}")

        for line in stdout:
            line = line.rstrip()
            logging.info(line)
            if not line or line == "\x07":
                continue

            if any([line_to_skip in line for line_to_skip in self.lines_to_skip]):
                continue

            # print(f"got line: {line}")

            if "Error:" in line:
                raise CLICommandError(line)

            if respondto in line:
                logging.info(f"found {respondto} and sending {response}")
                stdin.write(response)
                stdin.flush()
            else:
                output.append(line)

        return output

    def disconnect(self):
        """Disconnect the ssh session."""
        self.ssh.close()

    def parse_generic_output(self, output, primary_key=None):
        """Parse generic output from a CLI command.

        :param output: the output from the command
        :param primary_key: the primary key for the command
        """
        data = {}
        # the current object
        current_object = None
        # the first key that we see
        first_key = None
        # the dictionary or current data that we have parsed
        temp_data = {}
        for line in output:
            line = line.strip()

            # check for an empty line
            # if not, continue to the next line
            if not line:
                continue
            # check to see if we have a : in the line
            # if not, continue to the next line
            if ":" not in line:
                continue
            # check for lines to skip so we don't get bad data
            # if anything matches, continue to the next line
            if any([line_to_skip in line for line_to_skip in self.lines_to_skip]):
                continue

            try:
                slist = line.split(":")
                key = slist[0]
                value = ":".join(slist[1:])

            except ValueError:
                logging.error(f"bad line: {line}")
                continue

            key = key.strip()
            value = value.strip()

            if not primary_key:
                logging.info(f"setting primary_key to {key}")
                primary_key = key
            if not first_key:
                logging.info(f"setting first_key to {key}")
                first_key = key

            if primary_key == first_key and key == primary_key:
                logging.info(f"primary == first, setting current object to {value}")
                current_object = value
                if current_object not in data:
                    data[current_object] = {}
                continue

            if key == primary_key:
                logging.info(
                    f"primary_key != first_key, found primary key,"
                    f" setting current object to {value}"
                )
                current_object = value
                if temp_data:
                    logging.info("have temp_data")
                    data[current_object] = temp_data
                    temp_data = {}

            if key == first_key:
                logging.info(
                    "primary_key != first_key, found first key, "
                    "setting current_object to None, updating temp_data"
                )
                current_object = None
                temp_data = {}
                temp_data[key] = value

            if current_object:
                data[current_object][key] = value
            else:
                temp_data[key] = value

        return data

    def run_command_python_api(self, command, privilege_level="admin", **kwargs):
        """Run a command through the Python API.

        Note: the fields that are returned must be specified in the fields
        """
        logging.info(
            f'{self.name} - running "{command}" with arguments'
            f" {kwargs} and privilege: {privilege_level}"
        )
        with HostConnection(
            self.host, username=self.username, password=self.password, verify=False
        ):
            response = CLI().execute(command, privilege_level=privilege_level, **kwargs)
            print(json.dumps(response.http_response.json(), indent=4))
