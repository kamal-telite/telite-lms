param(
  [string]$BaseUrl = "http://localhost:3000",
  [string]$CourseId = "course-frontend-basics",
  [string]$Username = "anika"
)

$ErrorActionPreference = "Stop"

if (-not $env:TELITE_SMOKE_PASSWORD) {
  throw "Set TELITE_SMOKE_PASSWORD before running this smoke test."
}

function Invoke-TeliteJson {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null
  )

  $params = @{
    Uri = "$BaseUrl$Path"
    Method = $Method
    WebSession = $script:Session
  }

  if ($null -ne $Body) {
    $params.ContentType = "application/json"
    $params.Body = ($Body | ConvertTo-Json -Depth 8)
  }

  Invoke-RestMethod @params
}

Invoke-RestMethod `
  -Uri "$BaseUrl/auth/login" `
  -Method Post `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=$Username&password=$($env:TELITE_SMOKE_PASSWORD)" `
  -SessionVariable Session | Out-Null

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$createdSection = $null
$moveSection = $null
$createdModule = $null
$duplicatedModule = $null
$duplicatedSection = $null

try {
  $builder = Invoke-TeliteJson -Method Get -Path "/authoring/courses/$CourseId/builder"
  $sectionOrder = @($builder.sections).Count

  $createdSection = Invoke-TeliteJson `
    -Method Post `
    -Path "/authoring/courses/$CourseId/sections" `
    -Body @{ title = "Smoke Section $stamp"; sort_order = $sectionOrder }

  $moduleResponse = Invoke-TeliteJson `
    -Method Post `
    -Path "/authoring/modules" `
    -Body @{
      course_id = $CourseId
      section = $createdSection.sort_order
      section_id = $createdSection.id
      title = "Smoke Module $stamp"
      module_type = "page"
    }
  $createdModule = $moduleResponse.module

  $duplicatedModuleResponse = Invoke-TeliteJson `
    -Method Post `
    -Path "/authoring/modules/$($createdModule.id)/duplicate"
  $duplicatedModule = $duplicatedModuleResponse.module

  $moveSection = Invoke-TeliteJson `
    -Method Post `
    -Path "/authoring/courses/$CourseId/sections" `
    -Body @{ title = "Smoke Move Section $stamp"; sort_order = ($sectionOrder + 1) }

  Invoke-TeliteJson `
    -Method Put `
    -Path "/authoring/courses/$CourseId/structure" `
    -Body @{
      updates = @(
        @{
          section_id = $createdSection.id
          modules = @(@{ module_id = $createdModule.id; sort_order = 0 })
        },
        @{
          section_id = $moveSection.id
          modules = @(@{ module_id = $duplicatedModule.id; sort_order = 0 })
        }
      )
    } | Out-Null

  $duplicatedSectionResponse = Invoke-TeliteJson `
    -Method Post `
    -Path "/authoring/courses/$CourseId/sections/$($createdSection.id)/duplicate"
  $duplicatedSection = $duplicatedSectionResponse.section

  $builderAfter = Invoke-TeliteJson -Method Get -Path "/authoring/courses/$CourseId/builder"
  $sectionVisible = @($builderAfter.sections | Where-Object { $_.id -eq $duplicatedSection.id }).Count
  $moduleVisible = @($builderAfter.sections.modules | Where-Object { $_.id -eq $duplicatedModule.id }).Count
  $movedModule = @($builderAfter.sections.modules | Where-Object { $_.id -eq $duplicatedModule.id })[0]

  if ($sectionVisible -ne 1 -or $moduleVisible -ne 1) {
    throw "Duplicated section/module did not appear in builder payload."
  }
  if (-not $movedModule -or $movedModule.section_id -ne $moveSection.id) {
    throw "Cross-section module move did not persist."
  }

  Write-Host "BUILDER_SMOKE_OK course=$CourseId duplicatedSection=$($duplicatedSection.id) duplicatedModule=$($duplicatedModule.id) movedModule=$($duplicatedModule.id)"
}
finally {
  if ($duplicatedSection -and $duplicatedSection.modules) {
    foreach ($module in @($duplicatedSection.modules)) {
      try { Invoke-TeliteJson -Method Delete -Path "/authoring/modules/$($module.id)" | Out-Null } catch {}
    }
    try { Invoke-TeliteJson -Method Delete -Path "/authoring/courses/$CourseId/sections/$($duplicatedSection.id)" | Out-Null } catch {}
  }
  if ($duplicatedModule) {
    try { Invoke-TeliteJson -Method Delete -Path "/authoring/modules/$($duplicatedModule.id)" | Out-Null } catch {}
  }
  if ($moveSection) {
    try { Invoke-TeliteJson -Method Delete -Path "/authoring/courses/$CourseId/sections/$($moveSection.id)" | Out-Null } catch {}
  }
  if ($createdModule) {
    try { Invoke-TeliteJson -Method Delete -Path "/authoring/modules/$($createdModule.id)" | Out-Null } catch {}
  }
  if ($createdSection) {
    try { Invoke-TeliteJson -Method Delete -Path "/authoring/courses/$CourseId/sections/$($createdSection.id)" | Out-Null } catch {}
  }
}
