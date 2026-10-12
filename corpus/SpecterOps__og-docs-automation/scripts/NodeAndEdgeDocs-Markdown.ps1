<#
    Internal Markdown transformation helpers for Render-NodeAndEdgeDocs.ps1.
#>

function Get-ExtensionSlug {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $ExtensionName
    )

    [string] $slug = $ExtensionName.ToLower()
    if ($slug -match '^so[a-z0-9]') {
        return $slug.Substring(2)
    }

    return $slug
}

function Test-IsKnownKind {
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $KindName
    )

    return ($script:NodeKindLookup.ContainsKey($KindName) -or $script:EdgeKindLookup.ContainsKey($KindName))
}

function ConvertTo-YamlSingleQuoted {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Value
    )

    return "'" + $Value.Replace("'", "''") + "'"
}

function Convert-ImagePaths {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    [regex] $imageRegex = [regex]'!\[([^\]]*)\]\(([^)]+)\)'

    return $imageRegex.Replace($Markdown, {
            param([System.Text.RegularExpressions.Match] $match)

            [string] $altText = $match.Groups[1].Value
            [string] $rawTarget = $match.Groups[2].Value.Trim()

            if ($rawTarget -match '^(?i:https?:|data:|/)') {
                return $match.Value
            }

            [string] $imagePath = $rawTarget
            [string] $titleSuffix = ''
            if ($rawTarget -match '^(\S+)\s+(("[^"]*")|(''[^'']*''))$') {
                $imagePath = $matches[1]
                $titleSuffix = ' ' + $matches[2]
            }

            [string] $pathWithoutQuery = ($imagePath -split '[?#]', 2)[0]
            [string] $fileName = [System.IO.Path]::GetFileName($pathWithoutQuery)

            if ([string]::IsNullOrWhiteSpace($fileName)) {
                return $match.Value
            }

            return '![{0}]({1}/{2}{3})' -f $altText, $IconBasePath, $fileName.ToLower(), $titleSuffix
        })
}

function Get-KindLinkPath {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $KindName,

        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string] $CurrentKindName
    )

    if (-not [string]::IsNullOrWhiteSpace($CurrentKindName) -and $KindName -eq $CurrentKindName) {
        return ''
    }

    if ($script:NodeKindLookup.ContainsKey($KindName)) {
        return ('{0}/nodes/{1}' -f $DocsBasePath, $KindName.ToLower())
    }

    if ($script:EdgeKindLookup.ContainsKey($KindName)) {
        return ('{0}/edges/{1}' -f $DocsBasePath, $KindName.ToLower())
    }

    return ''
}

function Protect-MarkdownPatterns {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ref] $Store,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string[]] $Patterns
    )

    foreach ($pattern in $Patterns) {
        $Markdown = [regex]::Replace($Markdown, $pattern, {
                param([System.Text.RegularExpressions.Match] $match)

                [string] $token = "%%MDXPROTECT$($Store.Value.Count)%%"
                $Store.Value[$token] = $match.Value
                return $token
            })
    }

    return $Markdown
}

function Convert-KindReferences {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string] $CurrentKindName
    )

    if (($script:NodeKindLookup.Count + $script:EdgeKindLookup.Count) -eq 0) {
        return $Markdown
    }

    [string[]] $allKinds = @(
        $script:NodeKindLookup.Keys +
        $script:EdgeKindLookup.Keys |
        Sort-Object -Unique |
        Sort-Object { $_.Length } -Descending
    )

    $Markdown = [regex]::Replace($Markdown, '(?<!`)`(?<code>[^`\r\n]+)`(?!`)', {
            param([System.Text.RegularExpressions.Match] $match)

            [string] $kindName = $match.Groups['code'].Value
            if (-not (Test-IsKnownKind -KindName $kindName)) {
                return $match.Value
            }

            [string] $path = Get-KindLinkPath -KindName $kindName -CurrentKindName $CurrentKindName
            if ([string]::IsNullOrWhiteSpace($path)) {
                return $match.Value
            }

            return '[{0}]({1})' -f $kindName, $path.ToLower()
        })

    [hashtable] $protected = @{}
    $Markdown = Protect-MarkdownPatterns -Markdown $Markdown -Store ([ref] $protected) -Patterns @(
        '(?s)```.*?```',
        '!\[[^\]]*\]\([^)]+\)',
        '(?<!!)\[[^\]]+\]\([^)]+\)',
        '(?<!`)`[^`]+`(?!`)'
    )

    foreach ($kindName in $allKinds) {
        [string] $path = Get-KindLinkPath -KindName $kindName -CurrentKindName $CurrentKindName
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }

        [string] $kindPattern = '(?<![A-Za-z0-9_/\[])' + [regex]::Escape($kindName) + '(?![A-Za-z0-9_])'
        [string] $replacement = '[{0}]({1})' -f $kindName, $path.ToLower()

        $Markdown = [regex]::Replace($Markdown, $kindPattern, {
                param([System.Text.RegularExpressions.Match] $match)
                return $replacement
            })
    }

    foreach ($token in $protected.Keys) {
        $Markdown = $Markdown.Replace($token, [string] $protected[$token])
    }

    return $Markdown
}

function Convert-MarkdownLinks {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $SiblingBasePath,

        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string] $CurrentKindName
    )

    [regex] $linkRegex = [regex]'(?<!!)\[([^\]]+)\]\(([^)]+)\)'

    return $linkRegex.Replace($Markdown, {
            param([System.Text.RegularExpressions.Match] $match)

            [string] $linkText = $match.Groups[1].Value
            [string] $rawTarget = $match.Groups[2].Value.Trim()

            if ($rawTarget -match '^(?i:https?:|mailto:|data:|/)') {
                return $match.Value
            }

            [string] $linkPath = $rawTarget
            [string] $titleSuffix = ''
            if ($rawTarget -match '^(\S+)\s+(("[^"]*")|(''[^'']*''))$') {
                $linkPath = $matches[1]
                $titleSuffix = ' ' + $matches[2]
            }

            [string] $pathWithoutQuery = ($linkPath -split '[?#]', 2)[0]
            if ($pathWithoutQuery -notmatch '\.md$') {
                return $match.Value
            }

            [string] $baseName = [System.IO.Path]::GetFileNameWithoutExtension($pathWithoutQuery)
            [string] $rewrittenPath = Get-KindLinkPath -KindName $baseName -CurrentKindName $CurrentKindName

            if ([string]::IsNullOrWhiteSpace($rewrittenPath)) {
                if (-not [string]::IsNullOrWhiteSpace($CurrentKindName) -and $baseName -eq $CurrentKindName) {
                    return $linkText
                }

                $rewrittenPath = $linkPath -replace '\.md(?=($|[?#]))', ''
                if ($rewrittenPath -notmatch '[/\\]') {
                    $rewrittenPath = $SiblingBasePath + '/' + $rewrittenPath
                }
            }

            return '[{0}]({1}{2})' -f $linkText, $rewrittenPath.ToLower(), $titleSuffix
        })
}

function Convert-Callouts {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    [regex] $calloutRegex = [regex]'(?m)^> \[!(NOTE|IMPORTANT|WARNING|TIP|CAUTION)\]\r?\n(?:^> .*(?:\r?\n|$))+'

    return $calloutRegex.Replace($Markdown, {
            param([System.Text.RegularExpressions.Match] $match)

            [string] $type = $match.Groups[1].Value
            [string] $tag = switch ($type) {
                'NOTE' { 'Info' }
                'IMPORTANT' { 'Note' }
                'WARNING' { 'Warning' }
                'TIP' { 'Tip' }
                'CAUTION' { 'Danger' }
            }

            [string[]] $contentLines = $match.Value -split '\r?\n' |
                Select-Object -Skip 1 |
                Where-Object { $_ -ne '' } |
                ForEach-Object { $_ -replace '^> ?', '' }

            [string] $body = ($contentLines -join "`n").TrimEnd()
            return "<$tag>`n$body`n</$tag>"
        })
}

function Remove-H1Headers {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    return ($Markdown -replace '(?m)^# .+\r?\n\r?\n', '').Trim()
}

function Remove-InitialDescriptionHeading {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    return [regex]::Replace($Markdown, '\A[ \t]*## Description[ \t]*\r?\n(?:\r?\n)?', '').Trim()
}

function Get-MarkdownSection {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Heading
    )

    [string] $pattern = '(?ms)^## ' + [regex]::Escape($Heading) + '\s*\r?\n(?<body>.*?)(?=^## |\z)'
    [System.Text.RegularExpressions.Match] $match = [regex]::Match($Markdown, $pattern)

    if (-not $match.Success) {
        return ''
    }

    return $match.Groups['body'].Value.Trim()
}

function Get-MarkdownSubsection {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Heading
    )

    [string] $pattern = '(?ms)^### ' + [regex]::Escape($Heading) + '\s*\r?\n(?<body>.*?)(?=^### |\z)'
    [System.Text.RegularExpressions.Match] $match = [regex]::Match($Markdown, $pattern)

    if (-not $match.Success) {
        return ''
    }

    return $match.Groups['body'].Value.Trim()
}

function Get-FirstMarkdownTable {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    [System.Text.RegularExpressions.Match] $match = [regex]::Match($Markdown, '(?m)^\|.*\r?\n^\|[-:| ]+\|.*(?:\r?\n^\|.*)+')
    if (-not $match.Success) {
        return ''
    }

    return $match.Value.Trim()
}

function Get-FirstMermaidBlock {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    [System.Text.RegularExpressions.Match] $match = [regex]::Match($Markdown, '(?s)```mermaid\r?\n.*?```')
    if (-not $match.Success) {
        return ''
    }

    return $match.Value.Trim()
}

function Remove-DuplicateMermaidRelationships {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    if ([string]::IsNullOrWhiteSpace($Markdown)) {
        return $Markdown
    }

    [regex] $relationshipRegex = [regex]'^\s*(?<start>\S+)\s+--\s+(?<kind>.+?)\s+-->\s+(?<end>\S+)\s*$'
    [System.Collections.Generic.HashSet[string]] $seenRelationships = [System.Collections.Generic.HashSet[string]]::new()
    [System.Collections.Generic.List[string]] $lines = [System.Collections.Generic.List[string]]::new()

    foreach ($line in ($Markdown -split '\r?\n')) {
        [System.Text.RegularExpressions.Match] $match = $relationshipRegex.Match($line)
        if ($match.Success) {
            [string] $key = '{0}|{1}|{2}' -f (
                $match.Groups['start'].Value,
                $match.Groups['kind'].Value,
                $match.Groups['end'].Value
            )
            if (-not $seenRelationships.Add($key)) {
                continue
            }
        }

        $lines.Add($line)
    }

    return $lines -join "`n"
}

function Convert-CollectorMermaidNodes {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    return [regex]::Replace(
        $Markdown,
        '(?m)^(?<indent>[ \t]*)(?<id>[A-Za-z_][A-Za-z0-9_]*)\["[^"\r\n]*"\]:::bhNode[ \t]*\r?$',
        {
            param([System.Text.RegularExpressions.Match] $match)

            return '{0}{1}["{1}"]' -f $match.Groups['indent'].Value, $match.Groups['id'].Value
        }
    )
}

function Sort-CollectorMermaidDiagram {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown
    )

    if ([string]::IsNullOrWhiteSpace($Markdown)) {
        return $Markdown
    }

    [regex] $nodeDeclarationRegex = [regex]'^(?<indent>[ \t]*)(?<id>[A-Za-z_][A-Za-z0-9_]*)\["[^"\r\n]*"\][ \t]*$'
    [regex] $relationshipRegex = [regex]'^\s*(?<start>\S+)\s+--\s+(?<kind>.+?)\s+-->\s+(?<end>\S+)\s*$'
    [string[]] $sourceLines = @($Markdown -split '\r?\n')

    [psobject[]] $nodeDeclarations = @(
        foreach ($line in $sourceLines) {
            [System.Text.RegularExpressions.Match] $match = $nodeDeclarationRegex.Match($line)
            if ($match.Success) {
                [PSCustomObject]@{
                    Id   = $match.Groups['id'].Value
                    Line = $line
                }
            }
        }
    )
    [psobject[]] $sortedNodeDeclarations = @($nodeDeclarations | Sort-Object -Property Id)

    [psobject[]] $relationships = @(
        foreach ($line in $sourceLines) {
            [System.Text.RegularExpressions.Match] $match = $relationshipRegex.Match($line)
            if ($match.Success) {
                [PSCustomObject]@{
                    Start = $match.Groups['start'].Value
                    Kind  = $match.Groups['kind'].Value
                    End   = $match.Groups['end'].Value
                    Line  = $line
                }
            }
        }
    )
    [psobject[]] $sortedRelationships = @($relationships | Sort-Object -Property Start, Kind, End)

    [System.Collections.Generic.List[string]] $sortedLines = [System.Collections.Generic.List[string]]::new()
    [int] $nodeIndex = 0
    [int] $relationshipIndex = 0
    foreach ($line in $sourceLines) {
        if ($nodeDeclarationRegex.IsMatch($line)) {
            $sortedLines.Add([string] $sortedNodeDeclarations[$nodeIndex].Line)
            $nodeIndex++
        }
        elseif ($relationshipRegex.IsMatch($line)) {
            $sortedLines.Add([string] $sortedRelationships[$relationshipIndex].Line)
            $relationshipIndex++
        }
        else {
            $sortedLines.Add($line)
        }
    }

    return $sortedLines -join "`n"
}

function Join-MarkdownSections {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [object[]] $Sections
    )

    [string[]] $nonEmptySections = @(
        $Sections |
        ForEach-Object {
            if ($null -eq $_) {
                return
            }

            [string] $_
        } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )

    return (($nonEmptySections -join "`n`n").Trim())
}

function Convert-BodyMarkdown {
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Markdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $SiblingBasePath,

        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string] $CurrentKindName
    )

    $Markdown = Remove-H1Headers -Markdown $Markdown
    $Markdown = Convert-ImagePaths -Markdown $Markdown
    $Markdown = Convert-KindReferences -Markdown $Markdown -CurrentKindName $CurrentKindName
    $Markdown = Convert-MarkdownLinks -Markdown $Markdown -SiblingBasePath $SiblingBasePath -CurrentKindName $CurrentKindName
    $Markdown = Convert-Callouts -Markdown $Markdown
    $Markdown = [regex]::Replace($Markdown, '(?s)```mermaid\r?\n.*?```', {
            param([System.Text.RegularExpressions.Match] $match)
            return $match.Value -replace '(?<!\\)@', '\@'
        })
    $Markdown = $Markdown.Replace('https://bloodhound.specterops.io/', '/')

    return $Markdown.Trim()
}

function New-OfficialDoc {
    [OutputType([void])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $Name,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Description,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $BodyMarkdown,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $OutputFilePath,

        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string] $IconPath
    )

    [string] $iconLine = ''
    if (-not [string]::IsNullOrWhiteSpace($IconPath)) {
        $iconLine = ('icon: {0}' -f (ConvertTo-YamlSingleQuoted -Value $IconPath)) + "`r`n"
    }

    [string] $mdx = @'
---
title: {0}
description: {1}
{2}---

<img noZoom src="/assets/enterprise-AND-community-edition-pill-tag.svg" alt="Applies to BloodHound Enterprise and CE"/>

{3}
'@ -f (
        (ConvertTo-YamlSingleQuoted -Value $Name),
        (ConvertTo-YamlSingleQuoted -Value $Description),
        $iconLine,
        $BodyMarkdown.TrimEnd()
    )

    $mdx = $mdx -replace "`r?`n", "`r`n"

    Set-Content -Path $OutputFilePath -Value $mdx -Encoding UTF8
    Write-Host "Wrote $OutputFilePath" -ForegroundColor DarkGray
}
