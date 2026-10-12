<#
.SYNOPSIS
    Generates MDX documentation pages for nodes and edges.

.DESCRIPTION
    Reads node kinds and edge kinds from the BloodHound extension schema and
    creates one MDX file per kind under docs/official-docs/opengraph/extensions/<ExtensionName>.

    Generated files contain frontmatter and the content from descriptions/nodes or descriptions/edges.

    The following transformations are applied to the description content:
    - H1 headers are removed (the MDX frontmatter title is used instead).
    - Refs to known node and edge kinds are converted into links using the DocsBasePath parameter.
    - Links to other markdown files have their .md extension stripped.
    - GitHub-flavored callouts (NOTE, IMPORTANT, WARNING, TIP, CAUTION) are converted to Mintlify components.
    - "@" characters inside mermaid code blocks are escaped as "\@" (if not already escaped) to prevent MDX parsing issues.
    - OpenHound collector graph metadata is loaded directly from the collector using the same rendering pipeline as
      `openhound create docs`; a pre-generated docs/graph directory is not required.
    - Node documentation includes an Edges section from the collector, including the mermaid diagram plus inbound and
      outbound tables, and a Properties table with inherited fields, types, and docstring descriptions.
    - Edge documentation includes an Edge Schema section before General Information, including traversability, the
      source/destination node table, and the mermaid diagram sourced from the collector.
#>

#Requires -Version 5.1

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ExtensionSchemaPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ExtensionShortName,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $NodeDescriptionsDir = (Join-Path -Path $PSScriptRoot -ChildPath '../../../descriptions/nodes'),

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $EdgeDescriptionsDir = (Join-Path -Path $PSScriptRoot -ChildPath '../../../descriptions/edges'),

    [Parameter(Mandatory = $false)]
    [AllowEmptyString()]
    [string] $CollectorName = '',

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $CollectorProjectDir = (Join-Path -Path $PSScriptRoot -ChildPath '../../..'),

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $OutputDir = (Join-Path -Path $PSScriptRoot -ChildPath '../../official-docs/opengraph/extensions'),

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $IconBasePath = 'icons',

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string] $DocsBasePath = '..',

    [Parameter(Mandatory = $false)]
    [bool] $OpenHoundStructure = $true
)

Set-StrictMode -Version Latest

[hashtable] $script:NodeKindLookup = @{}
[hashtable] $script:EdgeKindLookup = @{}
[hashtable] $script:CollectorNodeDocs = @{}
[hashtable] $script:CollectorEdgeDocs = @{}

. (Join-Path -Path $PSScriptRoot -ChildPath 'NodeAndEdgeDocs-Collector.ps1')
. (Join-Path -Path $PSScriptRoot -ChildPath 'NodeAndEdgeDocs-Markdown.ps1')

function Get-NodeGraphSections {
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $NodeName,

        [Parameter(Mandatory = $true)]
        [hashtable] $RelationshipKindMap
    )

    if (-not $script:CollectorNodeDocs.ContainsKey($NodeName)) {
        Write-Warning "Collector graph metadata not found for node '$NodeName'."
        return [PSCustomObject]@{
            Edges      = ''
            Properties = ''
        }
    }

    [string] $content = $script:CollectorNodeDocs[$NodeName]
    [string] $edgeSection = Get-MarkdownSection -Markdown $content -Heading 'Edges'
    [string] $propertiesSection = Get-MarkdownSection -Markdown $content -Heading 'Node properties'

    [string] $mermaid = Get-FirstMermaidBlock -Markdown $edgeSection
    $mermaid = Convert-CollectorMermaidNodes -Markdown $mermaid
    $mermaid = Remove-DuplicateMermaidRelationships -Markdown $mermaid
    $mermaid = Sort-CollectorMermaidDiagram -Markdown $mermaid
    [string] $incoming = Get-MarkdownSubsection -Markdown $edgeSection -Heading 'Incoming'
    [string] $outgoing = Get-MarkdownSubsection -Markdown $edgeSection -Heading 'Outgoing'

    [string[]] $incomingRows = @(Convert-CollectorNodeEdgeRows -Markdown $incoming -Direction 'Inbound' -RelationshipKindMap $RelationshipKindMap)
    [string[]] $outgoingRows = @(Convert-CollectorNodeEdgeRows -Markdown $outgoing -Direction 'Outbound' -RelationshipKindMap $RelationshipKindMap)

    [string] $incomingMarkdown = Format-EdgeTable -Heading 'Inbound Edges' -PeerColumnName 'Source Node Types' -Rows $incomingRows -EmptyMessage "No inbound edges are defined by the $ExtensionShortName extension for this node."
    [string] $outgoingMarkdown = Format-EdgeTable -Heading 'Outbound Edges' -PeerColumnName 'Destination Node Types' -Rows $outgoingRows -EmptyMessage "No outbound edges are defined by the $ExtensionShortName extension for this node."

    [string] $edgeNoteMarkdown = "<Note>`nThe tables below list edges defined by the $ExtensionShortName extension only. Additional edges to or from this node may be created by other extensions.`n</Note>"

    [string] $edgesMarkdown = Join-MarkdownSections -Sections @(
        '## Edges',
        $edgeNoteMarkdown,
        $mermaid,
        $incomingMarkdown,
        $outgoingMarkdown
    )

    [string] $propertiesMarkdown = ''
    if (-not [string]::IsNullOrWhiteSpace($propertiesSection)) {
        $propertiesMarkdown = "## Properties`n`n$propertiesSection"
    }

    return [PSCustomObject]@{
        Edges      = $edgesMarkdown
        Properties = $propertiesMarkdown
    }
}

function Get-EdgeSchemaSection {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $EdgeName,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Traversable
    )

    [string] $traversableDisplay = Convert-TraversableToEmoji -Traversable $Traversable

    if (-not $script:CollectorEdgeDocs.ContainsKey($EdgeName)) {
        Write-Warning "Collector graph metadata not found for edge '$EdgeName'."
        return "## Edge Schema`n`n- Traversable: $traversableDisplay"
    }

    [string] $content = $script:CollectorEdgeDocs[$EdgeName]
    [string] $sourceDestSection = Get-MarkdownSection -Markdown $content -Heading 'Source and destination nodes'
    [string] $table = Get-FirstMarkdownTable -Markdown $sourceDestSection
    [string] $mermaid = Get-FirstMermaidBlock -Markdown $content
    $mermaid = Convert-CollectorMermaidNodes -Markdown $mermaid
    $mermaid = Sort-CollectorMermaidDiagram -Markdown $mermaid

    return Join-MarkdownSections -Sections @(
        '## Edge Schema',
        "- Traversable: $traversableDisplay",
        $table,
        $mermaid
    )
}

function Get-BasicEdgeSchemaSection {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Traversable
    )

    [string] $traversableDisplay = Convert-TraversableToEmoji -Traversable $Traversable
    return "## Edge Schema`n`n- Traversable: $traversableDisplay"
}

function Convert-TraversableToEmoji {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Traversable
    )

    if ($Traversable -eq 'true') {
        return '✅'
    }

    if ($Traversable -eq 'false') {
        return '❌'
    }

    return $Traversable
}

function Get-EdgeSchemaMap {
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $EdgeDescriptionsDir
    )

    [hashtable] $map = @{}
    [regex] $linkRegex = [regex]'\[([^\]]+)\]\(([^)]+)\)'

    foreach ($file in Get-ChildItem -Path $EdgeDescriptionsDir -Filter '*.md' -File) {
        [string] $content = Get-Content -Path $file.FullName -Raw
        [string] $edgeName = $file.BaseName
        [psobject[]] $sources = @()
        [psobject[]] $destinations = @()

        if ($content -match '(?m)^- Source:\s*(.+)$') {
            [string] $rawSourceLine = $matches[1]
            $sources = @($linkRegex.Matches($rawSourceLine) | ForEach-Object {
                    [PSCustomObject]@{
                        Name = $_.Groups[1].Value
                        Url  = $_.Groups[2].Value
                    }
                })
        }
        else {
            Write-Warning "Edge '$edgeName' ($($file.Name)): missing '- Source:' line."
        }

        if ($content -match '(?m)^- Destination:\s*(.+)$') {
            [string] $rawDestinationLine = $matches[1]
            $destinations = @($linkRegex.Matches($rawDestinationLine) | ForEach-Object {
                    [PSCustomObject]@{
                        Name = $_.Groups[1].Value
                        Url  = $_.Groups[2].Value
                    }
                })
        }
        else {
            Write-Warning "Edge '$edgeName' ($($file.Name)): missing '- Destination:' line."
        }

        $map[$edgeName] = [PSCustomObject]@{
            Sources      = $sources
            Destinations = $destinations
        }
    }

    return $map
}

function Format-EdgeTable {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Heading,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $PeerColumnName,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [string[]] $Rows,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $EmptyMessage
    )

    [string] $result = "### $Heading`n`n"
    if ($Rows.Count -gt 0) {
        $result += "| Edge Type | $PeerColumnName | Traversable |`n"
        $result += "| --------- | $('-' * $PeerColumnName.Length) | ----------- |`n"
        $result += ($Rows -join "`n")
    }
    else {
        $result += $EmptyMessage
    }

    return $result
}

function Convert-CollectorNodeEdgeRows {
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateSet('Inbound', 'Outbound')]
        [string] $Direction,

        [Parameter(Mandatory = $true)]
        [hashtable] $RelationshipKindMap
    )

    if ([string]::IsNullOrWhiteSpace($Markdown)) {
        return @()
    }

    [regex] $rowRegex = [regex]'(?m)^\|\s*\[(?<start>[^\]]+)\]\([^)]+\)\s*\|\s*\[(?<end>[^\]]+)\]\([^)]+\)\s*\|\s*\[(?<kind>[^\]]+)\]\([^)]+\)\s*\|.*\|\s*$'
    [hashtable] $edgeGroups = @{}

    foreach ($match in $rowRegex.Matches($Markdown)) {
        [string] $edgeName = $match.Groups['kind'].Value
        [string] $peerNodeName = if ($Direction -eq 'Inbound') {
            $match.Groups['start'].Value
        }
        else {
            $match.Groups['end'].Value
        }

        [string] $peerNodePath = Get-KindLinkPath -KindName $peerNodeName
        [string] $peerNodeDisplay = if ([string]::IsNullOrWhiteSpace($peerNodePath)) {
            $peerNodeName
        }
        else {
            '[{0}]({1})' -f $peerNodeName, $peerNodePath.ToLower()
        }

        if (-not $edgeGroups.ContainsKey($edgeName)) {
            [string] $edgePath = Get-KindLinkPath -KindName $edgeName
            [string] $edgeDisplay = if ([string]::IsNullOrWhiteSpace($edgePath)) {
                $edgeName
            }
            else {
                '[{0}]({1})' -f $edgeName, $edgePath.ToLower()
            }

            [psobject] $relationshipKind = $RelationshipKindMap[$edgeName]
            [string] $traversable = if ($null -ne $relationshipKind -and [bool] $relationshipKind.is_traversable) { 'true' } else { 'false' }
            $edgeGroups[$edgeName] = [PSCustomObject]@{
                Name        = $edgeName
                Display     = $edgeDisplay
                Traversable = Convert-TraversableToEmoji -Traversable $traversable
                Peers       = @{}
            }
        }

        $edgeGroups[$edgeName].Peers[$peerNodeName] = $peerNodeDisplay
    }

    return @(
        $edgeGroups.Values |
        Sort-Object -Property Name |
        ForEach-Object {
            [string[]] $peerDisplays = @(
                $_.Peers.GetEnumerator() |
                Sort-Object -Property Name |
                ForEach-Object { $_.Value }
            )

            '| {0} | {1} | {2} |' -f $_.Display, ($peerDisplays -join ', '), $_.Traversable
        }
    )
}

function Format-NodeReference {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [psobject] $NodeReference
    )

    [string] $nodeLinkPath = Get-KindLinkPath -KindName $NodeReference.Name
    if (-not [string]::IsNullOrWhiteSpace($nodeLinkPath)) {
        return '[{0}]({1})' -f $NodeReference.Name, $nodeLinkPath.ToLower()
    }

    if (-not [string]::IsNullOrWhiteSpace($NodeReference.Url)) {
        return '[{0}]({1})' -f $NodeReference.Name, $NodeReference.Url
    }

    return $NodeReference.Name
}

function New-NodeEdgeSectionMarkdown {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $NodeName,

        [Parameter(Mandatory = $true)]
        [hashtable] $EdgeSchemaMap,

        [Parameter(Mandatory = $true)]
        [hashtable] $RelationshipKindMap
    )

    [System.Collections.Generic.List[string]] $inboundRows = [System.Collections.Generic.List[string]]::new()
    [System.Collections.Generic.List[string]] $outboundRows = [System.Collections.Generic.List[string]]::new()

    foreach ($edgeName in ($EdgeSchemaMap.Keys | Sort-Object)) {
        [psobject] $schema = $EdgeSchemaMap[$edgeName]
        [string] $edgeLink = '[{0}]({1}/edges/{2})' -f $edgeName, $DocsBasePath, $edgeName.ToLower()
        [psobject] $relKind = $RelationshipKindMap[$edgeName]
        [string] $traversable = if ($relKind -and [bool] $relKind.is_traversable) { 'true' } else { 'false' }
        [string] $traversableDisplay = Convert-TraversableToEmoji -Traversable $traversable

        if ($NodeName -in $schema.Destinations.Name) {
            [string] $sourceLinks = ($schema.Sources | ForEach-Object {
                    Format-NodeReference -NodeReference $_
                }) -join ', '
            $inboundRows.Add("| $edgeLink | $sourceLinks | $traversableDisplay |")
        }

        if ($NodeName -in $schema.Sources.Name) {
            [string] $destinationLinks = ($schema.Destinations | ForEach-Object {
                    Format-NodeReference -NodeReference $_
                }) -join ', '
            $outboundRows.Add("| $edgeLink | $destinationLinks | $traversableDisplay |")
        }
    }

    return Join-MarkdownSections -Sections @(
        '## Edges',
        "<Note>`nThe tables below list edges defined by the $ExtensionShortName extension only. Additional edges to or from this node may be created by other extensions.`n</Note>",
        (Format-EdgeTable -Heading 'Inbound Edges' -PeerColumnName 'Source Node Types' -Rows $inboundRows -EmptyMessage "No inbound edges are defined by the $ExtensionShortName extension for this node."),
        (Format-EdgeTable -Heading 'Outbound Edges' -PeerColumnName 'Destination Node Types' -Rows $outboundRows -EmptyMessage "No outbound edges are defined by the $ExtensionShortName extension for this node.")
    )
}

function Add-NodeEdgeSections {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $EdgeSectionMarkdown
    )

    if ([string]::IsNullOrWhiteSpace($EdgeSectionMarkdown)) {
        return $Markdown
    }

    if ($Markdown -match '(?m)^## Properties\s*$') {
        return [regex]::Replace(
            $Markdown,
            '(?m)^## Properties\s*$',
            ($EdgeSectionMarkdown + "`r`n`r`n## Properties"),
            1
        )
    }

    return Join-MarkdownSections -Sections @(
        $Markdown,
        $EdgeSectionMarkdown
    )
}

function Add-TraversableToEdgeSchema {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Traversable
    )

    [string] $edgeSchemaHeading = '## Edge Schema'
    [string] $traversableEmoji = Convert-TraversableToEmoji -Traversable $Traversable
    [string] $traversableLine = "- Traversable: $traversableEmoji"

    if ($Markdown -match '(?m)^-?\s*Traversable:\s+(\S+)\s*$') {
        return $Markdown
    }

    if ($Markdown -match '(?m)^## Edge Schema\s*$') {
        if ($Markdown -match '(?ms)^## Edge Schema\s*\r?\n(?<schemaBody>.*?)(?:\r?\n## |\z)') {
            [string] $schemaBody = $matches['schemaBody']
            if ($schemaBody -match '(?m)^- Destination:\s+.+$') {
                return [regex]::Replace(
                    $Markdown,
                    '(?m)^(- Destination:\s+.+)$',
                    ('$1' + "`r`n" + $traversableLine),
                    1
                )
            }

            if ($schemaBody -match '(?m)^- Source:\s+.+$') {
                return [regex]::Replace(
                    $Markdown,
                    '(?m)^(- Source:\s+.+)$',
                    ('$1' + "`r`n" + $traversableLine),
                    1
                )
            }
        }

        return [regex]::Replace(
            $Markdown,
            '(?ms)^## Edge Schema\s*\r?\n(?:\r?\n)*',
            "$edgeSchemaHeading`r`n`r`n$traversableLine`r`n",
            1
        )
    }

    return Join-MarkdownSections -Sections @(
        (Get-BasicEdgeSchemaSection -Traversable $Traversable),
        $Markdown
    )
}

try {
    [psobject] $json = Get-Content -Path $ExtensionSchemaPath | ConvertFrom-Json
}
catch {
    Write-Error "Failed to parse extension file '$ExtensionSchemaPath': $($_.Exception.Message)"
    throw
}

[psobject[]] $nodeKinds = @($json.node_kinds | Sort-Object -Property name)
[psobject[]] $relationshipKinds = @($json.relationship_kinds | Sort-Object -Property name)
[string] $extensionName = [string] $json.schema.name

if ([string]::IsNullOrWhiteSpace($extensionName)) {
    throw "schema.name is missing in extension file: $ExtensionSchemaPath"
}

if ($OpenHoundStructure) {
    [string] $effectiveCollectorName = if ([string]::IsNullOrWhiteSpace($CollectorName)) {
        $ExtensionShortName
    }
    else {
        $CollectorName
    }
    Import-CollectorGraphDocs -Name $effectiveCollectorName
}

foreach ($nodeKind in $nodeKinds) {
    if (-not [string]::IsNullOrWhiteSpace([string] $nodeKind.name)) {
        $script:NodeKindLookup[[string] $nodeKind.name] = $true
    }
}

foreach ($relationshipKind in $relationshipKinds) {
    if (-not [string]::IsNullOrWhiteSpace([string] $relationshipKind.name)) {
        $script:EdgeKindLookup[[string] $relationshipKind.name] = $true
    }
}

[string] $extensionSlug = Get-ExtensionSlug -ExtensionName $extensionName
[string] $extensionOutputDir = Join-Path -Path $OutputDir -ChildPath $extensionSlug
[string] $nodesOutputDir = Join-Path -Path $extensionOutputDir -ChildPath 'nodes'
[string] $edgesOutputDir = Join-Path -Path $extensionOutputDir -ChildPath 'edges'
[hashtable] $relationshipKindMap = @{}

foreach ($relationshipKind in $relationshipKinds) {
    if (-not [string]::IsNullOrWhiteSpace([string] $relationshipKind.name)) {
        $relationshipKindMap[[string] $relationshipKind.name] = $relationshipKind
    }
}

[hashtable] $edgeSchemaMap = @{}
if (-not $OpenHoundStructure) {
    $edgeSchemaMap = Get-EdgeSchemaMap -EdgeDescriptionsDir $EdgeDescriptionsDir
}

foreach ($directory in @($nodesOutputDir, $edgesOutputDir)) {
    if (-not (Test-Path -Path $directory -PathType Container)) {
        New-Item -Path $directory -ItemType Directory -Force | Out-Null
    }
}

foreach ($nodeKind in $nodeKinds) {
    [string] $name = [string] $nodeKind.name
    [string] $description = [string] $nodeKind.description

    if ([string]::IsNullOrWhiteSpace($name)) {
        Write-Warning 'Skipping node kind with empty name.'
        continue
    }

    [string] $descriptionFilePath = Join-Path -Path $NodeDescriptionsDir -ChildPath "$name.md"
    if (-not (Test-Path -Path $descriptionFilePath -PathType Leaf)) {
        Write-Warning "Skipping ${name}: description file not found at $descriptionFilePath"
        continue
    }

    try {
        [string] $bodyMarkdown = Get-Content -Path $descriptionFilePath -Raw
        $bodyMarkdown = Remove-InitialDescriptionHeading -Markdown $bodyMarkdown
        if ($OpenHoundStructure) {
            [psobject] $graphSections = Get-NodeGraphSections -NodeName $name -RelationshipKindMap $relationshipKindMap
            $bodyMarkdown = Join-MarkdownSections -Sections @(
                $bodyMarkdown,
                $graphSections.Edges,
                $graphSections.Properties
            )
        }
        else {
            $bodyMarkdown = Add-NodeEdgeSections -Markdown $bodyMarkdown -EdgeSectionMarkdown (New-NodeEdgeSectionMarkdown -NodeName $name -EdgeSchemaMap $edgeSchemaMap -RelationshipKindMap $relationshipKindMap)
        }
        $bodyMarkdown = Convert-BodyMarkdown -Markdown $bodyMarkdown -SiblingBasePath "$DocsBasePath/nodes" -CurrentKindName $name

        [string] $outputFilePath = Join-Path -Path $nodesOutputDir -ChildPath "$($name.ToLower()).mdx"
        [string] $iconPath = "$IconBasePath/$($name.ToLower()).png"

        New-OfficialDoc -Name $name -Description $description -BodyMarkdown $bodyMarkdown -OutputFilePath $outputFilePath -IconPath $iconPath
    }
    catch {
        Write-Error "Error processing node kind '$name': $($_.Exception.Message)`nScriptStackTrace: $($_.ScriptStackTrace)"
        throw
    }
}

foreach ($relationshipKind in $relationshipKinds) {
    [string] $name = [string] $relationshipKind.name
    [string] $description = [string] $relationshipKind.description

    if ([string]::IsNullOrWhiteSpace($name)) {
        Write-Warning 'Skipping relationship kind with empty name.'
        continue
    }

    [string] $descriptionFilePath = Join-Path -Path $EdgeDescriptionsDir -ChildPath "$name.md"
    if (-not (Test-Path -Path $descriptionFilePath -PathType Leaf)) {
        Write-Warning "Skipping ${name}: description file not found at $descriptionFilePath"
        continue
    }

    try {
        [string] $traversable = if ([bool] $relationshipKind.is_traversable) { 'true' } else { 'false' }
        [string] $bodyMarkdown = Get-Content -Path $descriptionFilePath -Raw
        if ($OpenHoundStructure) {
            $bodyMarkdown = Join-MarkdownSections -Sections @(
                (Get-EdgeSchemaSection -EdgeName $name -Traversable $traversable),
                $bodyMarkdown
            )
        }
        else {
            $bodyMarkdown = Add-TraversableToEdgeSchema -Markdown $bodyMarkdown -Traversable $traversable
        }
        $bodyMarkdown = Convert-BodyMarkdown -Markdown $bodyMarkdown -SiblingBasePath "$DocsBasePath/edges" -CurrentKindName $name

        [string] $outputFilePath = Join-Path -Path $edgesOutputDir -ChildPath "$($name.ToLower()).mdx"

        New-OfficialDoc -Name $name -Description $description -BodyMarkdown $bodyMarkdown -OutputFilePath $outputFilePath
    }
    catch {
        Write-Error "Error processing relationship kind '$name': $($_.Exception.Message)`nScriptStackTrace: $($_.ScriptStackTrace)"
        throw
    }
}
