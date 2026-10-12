import hashlib
import json
import os
from io import BytesIO
from zipfile import ZipFile, ZipInfo

environments = []


class Synth:
    def __init__(self, buffer):
        self._zip_file = ZipFile(buffer)
        self._updates = dict()
        self._inserts = dict()
        self._deletes = list()
        self._manifest = json.loads(
            self._zip_file.open("manifest.json").read().decode(encoding="utf-8")
        )

    @staticmethod
    def md5(data):
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def sha256(data):
        return hashlib.sha256(data).hexdigest()

    @property
    def assemblies(self):
        assemblies = list()
        for key, val in self._manifest["artifacts"].items():
            if val["type"] == "cdk:cloud-assembly":
                assemblies.append(
                    Assembly(
                        key,
                        directory_name=val["properties"]["directoryName"],
                        zip_file=self._zip_file,
                    )
                )

        return assemblies

    @property
    def updated(self):
        return len(self._updates.keys()) > 0 or len(self._deletes) > 0

    def add_update(self, filename, data):
        self._updates[filename] = data

    def add_insert(self, filename, data):
        self._inserts[filename] = data

    def add_delete(self, filename):
        self._deletes.append(filename)

    def create_new_synth(self):
        synth = BytesIO()
        with ZipFile(synth, "w") as zip:
            for item in self._zip_file.filelist:
                if item.filename in self._deletes:
                    continue
                elif item.filename in self._updates:
                    zip.writestr(ZipInfo(item.filename), self._updates[item.filename])
                else:
                    zip.writestr(item, self._zip_file.read(item.filename))

            for filename, data in self._inserts.items():
                zip.writestr(ZipInfo(filename), data)

        return synth.getvalue()


class LambdaFunction:
    def __init__(self, id, directory_name, raw, zip_file):
        self.id = id
        self._directory_name = directory_name
        self._raw = raw
        self._zip_file = zip_file

    @property
    def function_name(self):
        return self._raw["Properties"]["FunctionName"]

    @property
    def handler_details(self):
        extension = "js"
        if self.runtime.startswith("python"):
            extension = "py"

        handler_details = self._raw["Properties"]["Handler"].split(".", 2)

        return f"{handler_details[0]}.{extension}", handler_details[1]

    @property
    def runtime(self):
        return self._raw["Properties"]["Runtime"]

    @property
    def clean_runtime(self):
        if self.runtime.startswith("python"):
            return "python"
        if self.runtime.startswith("nodejs"):
            return "nodejs"
        if self.runtime.startswith("java"):
            return "java"
        if self.runtime.startswith("go"):
            return "go"
        return self.runtime
    

    @property
    def absolute_handler_filename(self):
        filename, _ = self.handler_details
        return os.path.normpath(
            os.path.join(
                self._directory_name, self._raw["Metadata"]["aws:asset:path"], filename
            )
        )

    @property
    def resource(self):
        return self._raw

    def is_inline(self):
        return "ZipFile" in self._raw["Properties"]["Code"]

    def has_envs(self, envs):
        try:
            if all(
                item in self._raw["Properties"]["Environment"]["Variables"].items()
                for item in envs.items()
            ):
                return True
            return False
        except KeyError:
            return False

    def set_envs(self, envs):
        for key, value in envs.items():
            self.set_env(key, value)

    def set_env(self, key, value):
        try:
            self._raw["Properties"]["Environment"]["Variables"][key] = value
        except KeyError:
            self._raw["Properties"]["Environment"] = {"Variables": {[key]: value}}

    def get_hash(self):
        return self._raw["Properties"]["Code"]["S3Key"].split(".", 2)[0]

    def update_hash(self, hash):
        self._raw["Properties"]["Code"]["S3Key"] = f"{hash}.zip"
        self._raw["Metadata"]["aws:asset:path"] = f"../asset.{hash}"

    def get_handler(self):
        return (
            self._zip_file.open(self.absolute_handler_filename)
            .read()
            .decode(encoding="utf-8")
        )


class Stack:
    def __init__(self, id, directory_name, raw, zip_file):
        self.id = id
        self.absolute_filename = (
            f"{directory_name}/{raw['properties']['templateFile']}"
            if directory_name != ""
            else raw["properties"]["templateFile"]
        )
        self._directory_name = directory_name
        self._raw = raw
        self._template = json.loads(
            zip_file.open(self.absolute_filename).read().decode(encoding="utf-8")
        )
        self._zip_file = zip_file

    @property
    def stack_name(self):
        return self._raw["properties"]["stackName"]

    @property
    def environment(self):
        return self._raw["environment"]

    @property
    def template(self):
        return json.dumps(self._template, indent=2)

    @property
    def lambda_functions(self):
        lambdas = list()
        for key, val in self._template["Resources"].items():
            if val["Type"] == "AWS::Lambda::Function":
                lambdas.append(
                    LambdaFunction(
                        key,
                        directory_name=self._directory_name,
                        raw=val,
                        zip_file=self._zip_file,
                    )
                )

        return lambdas

    def replace_all(self, old, new):
        str_tpl = json.dumps(self._template)
        self._template = json.loads(str_tpl.replace(old, new))

    def has_resource(self, id):
        return id in self._template["Resources"]

    def get_resource(self, id):
        return self._template["Resources"][id]

    def set_resource(self, id, data):
        self._template["Resources"][id] = data


class AssetManifest:
    def __init__(self, id, directory_name, raw, zip_file):
        self.id = id
        self.absolut_filename = f"{directory_name}/{raw['properties']['file']}"
        self._directory_name = directory_name
        self._raw = raw
        self._manifest = json.loads(
            zip_file.open(self.absolut_filename).read().decode(encoding="utf-8")
        )
        self._zip_file = zip_file

    @property
    def manifest(self):
        return json.dumps(self._manifest, indent=2)

    def replace_hash(self, old, new):
        cfg = self._manifest["files"][old]
        del self._manifest["files"][old]
        cfg["source"]["path"] = f"../asset.{new}"
        cfg["destinations"]["current_account-current_region"][
            "objectKey"
        ] = f"{new}.zip"
        self._manifest["files"][new] = cfg


class Assembly:
    def __init__(self, id, directory_name, zip_file):
        self.id = id
        self._directory_name = directory_name
        self._zip_file = zip_file
        self._manifest = json.loads(
            zip_file.open(f"{self._directory_name}/manifest.json")
            .read()
            .decode(encoding="utf-8")
        )

    @property
    def stacks(self):
        stacks = list()
        for key, val in self._manifest["artifacts"].items():
            if val["type"] == "aws:cloudformation:stack":
                stack = Stack(
                    key,
                    directory_name=self._directory_name,
                    raw=val,
                    zip_file=self._zip_file,
                )
                if len(environments) > 0 and not stack.environment in environments:
                    continue

                stacks.append(stack)

        return stacks

    @property
    def asset_manifests(self):
        ams = list()
        for key, val in self._manifest["artifacts"].items():
            if val["type"] == "cdk:asset-manifest":
                ams.append(
                    AssetManifest(
                        key,
                        directory_name=self._directory_name,
                        raw=val,
                        zip_file=self._zip_file,
                    )
                )

        return ams
