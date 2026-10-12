<#
    Internal collector metadata helpers for Render-NodeAndEdgeDocs.ps1.
#>

function Convert-CollectorPropertyDirectives {
    [OutputType([void])]
    param()

    [regex] $directiveRegex = [regex]'(?m)^:::\s+(?<model>[A-Za-z_][A-Za-z0-9_.]*)[ \t]*\r?\n(?:^[ \t]+.*(?:\r?\n|$))*'
    [System.Collections.Generic.HashSet[string]] $modelPaths = [System.Collections.Generic.HashSet[string]]::new()

    foreach ($content in $script:CollectorNodeDocs.Values) {
        foreach ($match in $directiveRegex.Matches([string] $content)) {
            $null = $modelPaths.Add($match.Groups['model'].Value)
        }
    }

    if ($modelPaths.Count -eq 0) {
        return
    }

    [string] $propertyRenderer = @'
import dataclasses
import importlib
import inspect
import json
import os
import re
import types
import typing


def load_object(path):
    parts = path.split(".")
    for split_at in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:split_at])
        try:
            value = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name or module_name.startswith(f"{exc.name}."):
                continue
            raise

        for part in parts[split_at:]:
            value = getattr(value, part)
        return value

    raise ImportError(f"Unable to import property model {path!r}")


def attribute_descriptions(model):
    descriptions = {}
    item_pattern = re.compile(r"^\s+([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

    for base in reversed(model.__mro__):
        lines = inspect.cleandoc(base.__doc__ or "").splitlines()
        try:
            section_start = next(
                index for index, line in enumerate(lines) if line.strip() == "Attributes:"
            )
        except StopIteration:
            continue

        section_indent = len(lines[section_start]) - len(lines[section_start].lstrip())
        current_name = None
        current_indent = None
        for line in lines[section_start + 1 :]:
            stripped = line.strip()
            if not stripped:
                continue

            indent = len(line) - len(line.lstrip())
            if indent <= section_indent:
                break

            match = item_pattern.match(line)
            if match and (current_indent is None or indent <= current_indent):
                current_name = match.group(1)
                current_indent = indent
                descriptions[current_name] = match.group(2).strip()
            elif current_name:
                descriptions[current_name] = (
                    f"{descriptions[current_name]} {stripped}"
                ).strip()

    return descriptions


def format_type(annotation):
    if isinstance(annotation, str):
        return annotation
    if annotation is None or annotation is type(None):
        return "None"
    if isinstance(annotation, type):
        return annotation.__name__

    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        return " | ".join(format_type(item) for item in typing.get_args(annotation))

    return str(annotation).replace("typing.", "")


def escape_cell(value):
    return str(value).replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def render_table(path):
    model = load_object(path)
    descriptions = attribute_descriptions(model)

    try:
        resolved_types = typing.get_type_hints(model)
    except (NameError, TypeError):
        resolved_types = {}

    if dataclasses.is_dataclass(model):
        fields = [
            (
                field.name,
                resolved_types.get(field.name, field.type),
                field.metadata.get("description") if field.metadata else None,
            )
            for field in dataclasses.fields(model)
        ]
    elif hasattr(model, "model_fields"):
        fields = [
            (name, resolved_types.get(name, field.annotation), field.description)
            for name, field in model.model_fields.items()
        ]
    else:
        raise TypeError(f"Property model {path!r} is not a dataclass or Pydantic model")

    rows = [
        "| Property | Type | Description |",
        "| -------- | ---- | ----------- |",
    ]
    for name, annotation, field_description in fields:
        description = field_description or descriptions.get(name) or "-"
        rows.append(
            f"| `{escape_cell(name)}` | `{escape_cell(format_type(annotation))}` | "
            f"{escape_cell(description)} |"
        )
    return "\n".join(rows)


paths = json.loads(os.environ["OG_DOCS_PROPERTY_MODELS"])
print(json.dumps({path: render_table(path) for path in paths}))
'@

    $previousModelPaths = [Environment]::GetEnvironmentVariable('OG_DOCS_PROPERTY_MODELS', 'Process')
    try {
        [string[]] $sortedModelPaths = @($modelPaths | Sort-Object)
        [string] $modelPathsJson = ConvertTo-Json -InputObject $sortedModelPaths -Compress
        [Environment]::SetEnvironmentVariable('OG_DOCS_PROPERTY_MODELS', $modelPathsJson, 'Process')
        [string] $rawPropertyTables = (@(& uv run python -c $propertyRenderer) -join "`n")
        [int] $rendererExitCode = $LASTEXITCODE
    }
    finally {
        [Environment]::SetEnvironmentVariable('OG_DOCS_PROPERTY_MODELS', $previousModelPaths, 'Process')
    }

    if ($rendererExitCode -ne 0) {
        throw "Failed to render collector property tables (exit code $rendererExitCode)."
    }

    try {
        [psobject] $renderedTablesJson = $rawPropertyTables | ConvertFrom-Json
    }
    catch {
        throw "Failed to parse rendered collector property tables: $($_.Exception.Message)"
    }

    [hashtable] $renderedTables = @{}
    foreach ($property in $renderedTablesJson.PSObject.Properties) {
        $renderedTables[[string] $property.Name] = [string] $property.Value
    }

    foreach ($nodeName in @($script:CollectorNodeDocs.Keys)) {
        [string] $content = $script:CollectorNodeDocs[$nodeName]
        $script:CollectorNodeDocs[$nodeName] = $directiveRegex.Replace($content, {
                param([System.Text.RegularExpressions.Match] $match)

                [string] $modelPath = $match.Groups['model'].Value
                if ($renderedTables.ContainsKey($modelPath)) {
                    return $renderedTables[$modelPath]
                }

                return $match.Value
            })
    }
}

function Import-CollectorGraphDocs {
    [OutputType([void])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Name
    )

    if (-not (Get-Command -Name 'uv' -ErrorAction SilentlyContinue)) {
        throw "The 'uv' command is required to load graph metadata from the OpenHound collector."
    }

    if (-not (Test-Path -Path $CollectorProjectDir -PathType Container)) {
        throw "Collector project directory not found: $CollectorProjectDir"
    }

    Write-Host "Loading graph metadata from OpenHound collector '$Name'..." -ForegroundColor DarkGray
    # Use OpenHound's public docs command so collector discovery and decorator parsing stay owned by OpenHound.
    # The generated graph docs are only an interchange format and are removed before this function returns.
    [string] $temporaryDocsDir = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath ("OpenHound-Docs-{0}" -f [guid]::NewGuid().ToString('N'))
    New-Item -Path $temporaryDocsDir -ItemType Directory | Out-Null
    $previousLogPath = [Environment]::GetEnvironmentVariable('RUNTIME__LOG_PATH', 'Process')

    try {
        [Environment]::SetEnvironmentVariable('RUNTIME__LOG_PATH', (Join-Path -Path $temporaryDocsDir -ChildPath 'logs'), 'Process')
        Push-Location -Path $CollectorProjectDir
        try {
            & uv run openhound create docs $temporaryDocsDir
            [int] $createDocsExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }

        if ($createDocsExitCode -ne 0) {
            throw "Failed to generate graph metadata from OpenHound collector '$Name' (exit code $createDocsExitCode)."
        }

        [string] $graphDocsDir = Join-Path -Path $temporaryDocsDir -ChildPath 'graph'
        if (-not (Test-Path -Path $graphDocsDir -PathType Container)) {
            [string] $sourcesDir = Join-Path -Path $temporaryDocsDir -ChildPath 'sources'
            [System.IO.DirectoryInfo[]] $sourceDirectories = @()
            if (Test-Path -Path $sourcesDir -PathType Container) {
                $sourceDirectories = @(Get-ChildItem -Path $sourcesDir -Directory)
            }

            [System.IO.DirectoryInfo[]] $matchingSourceDirectories = @(
                $sourceDirectories | Where-Object { $_.Name -ieq $Name }
            )
            if ($matchingSourceDirectories.Count -eq 1) {
                $graphDocsDir = Join-Path -Path $matchingSourceDirectories[0].FullName -ChildPath 'graph'
            }
            elseif ($sourceDirectories.Count -eq 1) {
                $graphDocsDir = Join-Path -Path $sourceDirectories[0].FullName -ChildPath 'graph'
            }
            else {
                [string] $availableCollectors = ($sourceDirectories.Name | Sort-Object) -join ', '
                throw "Collector '$Name' could not be selected from generated docs. Available collectors: $availableCollectors"
            }
        }

        [string] $nodeDocsDir = Join-Path -Path $graphDocsDir -ChildPath 'nodes'
        [string] $edgeDocsDir = Join-Path -Path $graphDocsDir -ChildPath 'edges'
        if (-not (Test-Path -Path $nodeDocsDir -PathType Container)) {
            throw "Generated collector node documentation directory not found: $nodeDocsDir"
        }
        if (-not (Test-Path -Path $edgeDocsDir -PathType Container)) {
            throw "Generated collector edge documentation directory not found: $edgeDocsDir"
        }

        foreach ($file in Get-ChildItem -Path $nodeDocsDir -Filter '*.md' -File) {
            $script:CollectorNodeDocs[$file.BaseName] = Get-Content -Path $file.FullName -Raw
        }
        foreach ($file in Get-ChildItem -Path $edgeDocsDir -Filter '*.md' -File) {
            $script:CollectorEdgeDocs[$file.BaseName] = Get-Content -Path $file.FullName -Raw
        }

        Convert-CollectorPropertyDirectives
    }
    finally {
        [Environment]::SetEnvironmentVariable('RUNTIME__LOG_PATH', $previousLogPath, 'Process')
        if (Test-Path -Path $temporaryDocsDir -PathType Container) {
            Remove-Item -Path $temporaryDocsDir -Recurse -Force
        }
    }
}

