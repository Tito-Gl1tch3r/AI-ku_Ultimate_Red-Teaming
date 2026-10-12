import { test, expect } from './base.js';

let auditId;

async function expectSaveSucceeded(page) {
  await expect(page.getByRole('button', { name: /Saved/ })).toBeVisible();
}

function settingsWithPreservedSecrets(settings) {
  const copy = structuredClone(settings);
  if (copy.report?.private?.languageToolApiKeyConfigured)
    copy.report.private.languageToolApiKey = '••••••••••••••••';
  for (const field of [
    'openaiApiKey', 'anthropicApiKey', 'deepseekApiKey', 'ollamaApiKey',
    'bedrockApiKey', 'bedrockAccessKeyId', 'bedrockSecretAccessKey', 'bedrockSessionToken'
  ]) {
    if (copy.ai?.private?.[`${field}Configured`])
      copy.ai.private[field] = '••••••••••••••••';
  }
  return copy;
}

async function ensureFinding(request, title) {
  let audit = (await (await request.get(`/api/audits/${auditId}`)).json()).datas;
  let finding = audit.findings.find(entry => entry.title === title);
  if (!finding) {
    const response = await request.post(`/api/audits/${auditId}/findings`, {
      data: { title, vulnType: '' },
    });
    expect(response.ok()).toBeTruthy();
    audit = (await (await request.get(`/api/audits/${auditId}`)).json()).datas;
    finding = audit.findings.find(entry => entry.title === title);
  }
  expect(finding).toBeTruthy();
  return finding;
}

test.describe('Audit Edit Page', () => {

  // Setup: create only what data-setup doesn't provide (audit itself)
  // Language, vuln categories, audit type, and template already exist from data-setup
  test.beforeAll(async ({ request }) => {
    // Create an audit using the audit type and language from data-setup
    const auditRes = await request.post('/api/audits', {
      data: { name: 'E2E Test Audit', language: 'en', auditType: 'E2E Pentest', type: 'default' }
    });
    const auditData = await auditRes.json();
    auditId = auditData.datas.audit._id;
  });

  // No cleanup — audit persists for audits-list-with-data spec

  test.describe('Sidebar Navigation', () => {

    test('should display the audit edit sidebar with correct elements', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for sidebar to render (indicates audit data loaded)
      await expect(page.getByText('General Information')).toBeVisible();

      // Check audit type chip
      await expect(page.getByText(/^Audit$/).first()).toBeVisible();

      // Check sidebar navigation items
      await expect(page.getByText('General Information')).toBeVisible();
      await expect(page.getByText('Network Scan')).toBeVisible();
      await expect(page.getByText('Findings')).toBeVisible();

      // Check connected users section
      await expect(page.getByText('Users Connected')).toBeVisible();
    });

    test('should navigate to general information by default', async ({ page }) => {
      await page.goto(`/audits/${auditId}/general`);
      await expect(page.getByLabel(/Name/).first()).toBeVisible();

      // The breadcrumb should show the audit name and type
      await expect(page.getByText('E2E Test Audit (E2E Pentest)')).toBeVisible();

      // The general form should have key fields
      await expect(page.getByLabel(/Name/)).toBeVisible();
      await expect(page.getByLabel('Language')).toBeVisible();
      await expect(page.getByLabel('Template')).toBeVisible();
    });
  });

  test.describe('General Information', () => {

    test.beforeEach(async ({ page }) => {
      await page.goto(`/audits/${auditId}/general`);
      await expect(page.getByLabel(/Name/).first()).not.toHaveValue('');
    });

    test('should display all general information fields', async ({ page }) => {
      // Name field
      await expect(page.getByLabel(/Name/)).toBeVisible();

      // Language and Template selects
      await expect(page.getByLabel('Language')).toBeVisible();
      await expect(page.getByLabel('Template')).toBeVisible();

      // Company and Client selects
      await expect(page.getByLabel(/Company/)).toBeVisible();
      await expect(page.getByLabel(/Client/)).toBeVisible();

      // Collaborators
      await expect(page.getByLabel('Collaborators')).toBeVisible();

      // Date fields
      await expect(page.getByLabel(/Start Date/)).toBeVisible();
      await expect(page.getByLabel(/End Date/)).toBeVisible();
      await expect(page.getByLabel(/Reporting Date/)).toBeVisible();

      // Save button
      await expect(page.getByRole('button', { name: /Save/ })).toBeVisible();
    });

    test('should display the current audit name', async ({ page }) => {
      const nameField = page.getByLabel(/Name/).first();
      await expect(nameField).toHaveValue('E2E Test Audit');
    });

    test('should update audit name and save', async ({ page }) => {
      // Update the name
      const nameField = page.getByLabel(/Name/).first();
      await nameField.clear();
      await nameField.fill('E2E Test Audit Updated');

      // Click save
      await page.getByRole('button', { name: /Save/ }).click();

      // Verify saved button state
      await expectSaveSucceeded(page);

      // Revert the name back
      await nameField.clear();
      await nameField.fill('E2E Test Audit');
      await page.getByRole('button', { name: /Save/ }).click();
      await expectSaveSucceeded(page);
    });

    test('should set start and end dates', async ({ page }) => {
      const startDateField = page.getByLabel(/Start Date/).first();
      const endDateField = page.getByLabel(/End Date/).first();

      await startDateField.clear();
      await startDateField.fill('2025-01-01');
      await endDateField.clear();
      await endDateField.fill('2025-01-31');

      // Save
      await page.getByRole('button', { name: /Save/ }).click();
      await expectSaveSucceeded(page);

      // Verify dates are saved by reloading
      await page.reload();
      await expect(page.getByLabel(/Start Date/).first()).toBeVisible();

      await expect(page.getByLabel(/Start Date/).first()).toHaveValue('2025-01-01');
      await expect(page.getByLabel(/End Date/).first()).toHaveValue('2025-01-31');
    });

    test('should not save without a name', async ({ page }) => {
      const nameField = page.getByLabel(/Name/).first();

      // Clear the name
      await nameField.clear();

      // Try to save
      await page.getByRole('button', { name: /Save/ }).click();

      // Validation error should appear
      await expect(page.getByText('Field is required')).toBeVisible();

      // Revert by reloading
      await page.reload();
      await expect(page.getByLabel(/Name/).first()).toBeVisible();
    });
  });

  test.describe('Findings Management', () => {

    test('should navigate to add findings page', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for the sidebar to render (indicates audit data loaded)
      await expect(page.getByText('Findings')).toBeVisible();

      // Click the add button next to Findings
      await page.getByTestId('add-finding-button').click();
      await expect(page).toHaveURL(new RegExp(`/audits/${auditId}/findings/add`));
    });

    test('should create a finding with a custom title', async ({ page }) => {
      await page.goto(`/audits/${auditId}/findings/add`);
      await expect(page.getByLabel('Title')).toBeVisible();

      // Fill in a finding title
      const titleInput = page.getByLabel('Title');
      await titleInput.fill('Test SQL Injection Finding');

      // Click the Create dropdown button (inside the title input)
      await page.getByRole('button', { name: /^Expand "Create"$/ }).click();

      // Select "No Category" from the dropdown
      await page.getByText('No Category').click();

      // Should be redirected to the finding edit page
      await expect(page).toHaveURL(new RegExp(`/audits/${auditId}/findings/`));
    });

    test('should see created finding in the sidebar', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for the sidebar to render
      await expect(page.getByText('Findings')).toBeVisible();

      // The finding title should appear in the sidebar
      await expect(page.getByText('Test SQL Injection Finding')).toBeVisible();
    });

    test('should navigate to edit a finding by clicking on it in sidebar', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for the sidebar to render
      await expect(page.getByText('Findings')).toBeVisible();

      // Click on the finding in the sidebar
      await page.getByText('Test SQL Injection Finding').click();

      // Should navigate to the finding edit page
      await expect(page).toHaveURL(new RegExp(`/audits/${auditId}/findings/`));
    });
  });

  test.describe('AI and Quality Assurance', () => {

    test('should run built-in audit QA and navigate to the flagged finding', async ({ page, request }) => {
      const finding = await ensureFinding(request, 'Test SQL Injection Finding');

      await page.goto(`/audits/${auditId}/general`);
      await expect(page.getByLabel(/Name/).first()).not.toHaveValue('');
      await page.getByRole('button', { name: 'QA', exact: true }).click();
      await expect(page.getByText('QA Review', { exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Run Built-in Checks' }).click();

      await expect(page.getByText('Finding still in redaction', { exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Go to finding' }).click();
      await expect(page).toHaveURL(`/audits/${auditId}/findings/${finding._id}`);
      await expect(page.getByLabel('Title').first()).toHaveValue('Test SQL Injection Finding');
    });

    test('should generate, review, apply, and save an AI finding draft', async ({ page, request }) => {
      const settingsRes = await request.get('/api/settings');
      expect(settingsRes.ok()).toBeTruthy();
      const originalSettings = (await settingsRes.json()).datas;
      const enabledSettings = structuredClone(originalSettings);
      enabledSettings.ai.public.enabled = true;

      let originalPrompts;
      const prompt = {
        id: 'e2e-finding-rewrite',
        label: 'E2E finding rewrite',
        prompt: 'Rewrite this finding for an executive audience.',
        enabled: true,
      };

      try {
        const settingsUpdate = await request.put('/api/settings', {
          data: settingsWithPreservedSecrets(enabledSettings),
        });
        expect(settingsUpdate.ok()).toBeTruthy();

        const integrationRes = await request.get('/api/data/ai-integration');
        expect(integrationRes.ok()).toBeTruthy();
        originalPrompts = (await integrationRes.json()).datas.globalPrompts || [];
        const promptUpdate = await request.put('/api/data/ai-integration', {
          data: { globalPrompts: [...originalPrompts, prompt] },
        });
        expect(promptUpdate.ok()).toBeTruthy();

        await page.route('**/api/ai/generate', route => route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'event: done\ndata: {"draft":"<p>AI-generated description persisted.</p>","reply":"Draft ready for review."}\n\n',
        }));

        const finding = await ensureFinding(request, 'E2E AI Finding Draft');
        const findingUrl = `/audits/${auditId}/findings/${finding._id}`;

        await page.goto(findingUrl);
        await expect(page.getByRole('tab', { name: 'Definition' })).toBeVisible();
        await page.getByTestId('editor-ai-action').first().click();

        await expect(page.getByText('AI - Description', { exact: true })).toBeVisible();
        await expect(page.getByText('OpenAI', { exact: true })).toBeVisible();
        const promptSearch = page.getByPlaceholder('Search prompts...');
        await promptSearch.fill('E2E finding');
        await page.getByText(prompt.label, { exact: true }).click();

        const chatInput = page.getByPlaceholder('Ask anything');
        await expect(chatInput).toHaveValue(prompt.prompt);
        await page.getByRole('button', { name: 'Send', exact: true }).click();
        await expect(page.getByText('Draft ready for review.', { exact: true })).toBeVisible();
        await expect(page.getByText('AI-generated description persisted.', { exact: true })).toBeVisible();

        await page.getByRole('button', { name: 'Preview changes' }).click();
        await expect(page.getByRole('button', { name: 'Original response' })).toBeVisible();
        await page.getByRole('button', { name: 'Apply to field' }).click();

        await page.getByRole('listitem').filter({ hasText: 'Vulnerabilities' }).click();
        const leaveDialog = page.getByRole('dialog');
        await expect(leaveDialog.getByText('This field is locked for an active AI session. Leaving now will discard it.')).toBeVisible();
        await leaveDialog.getByRole('button', { name: 'Stay' }).click();
        await expect(page).toHaveURL(findingUrl);

        await page.getByRole('button', { name: /Save/ }).click();
        await expectSaveSucceeded(page);
        await page.getByText('AI - Description', { exact: true }).locator('..').getByRole('button').click();
        await expect(page.getByText('AI - Description', { exact: true })).not.toBeVisible();

        await page.reload();
        await expect(page.getByText('AI-generated description persisted.', { exact: true })).toBeVisible();
      }
      finally {
        if (originalPrompts)
          await request.put('/api/data/ai-integration', { data: { globalPrompts: originalPrompts } });
        await request.put('/api/settings', { data: settingsWithPreservedSecrets(originalSettings) });
      }
    });
  });

  test.describe('Network Scan', () => {

    test('should navigate to network scan page', async ({ page }) => {
      await page.goto(`/audits/${auditId}/network`);
      await expect(page.getByText('E2E Test Audit (E2E Pentest)')).toBeVisible();

      // The breadcrumb should show the audit name
      await expect(page.getByText('E2E Test Audit (E2E Pentest)')).toBeVisible();
    });
  });

  test.describe('Sidebar User Presence', () => {

    test('should show current user in connected users', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for the sidebar to render
      await expect(page.getByText('Findings')).toBeVisible();

      // Wait for socket connection to establish
      await page.waitForTimeout(1000);

      // The current user should appear in the connected users list
      await expect(page.getByText('Users Connected')).toBeVisible();
      await expect(page.getByText('admin (me)').first()).toBeVisible();
    });
  });

  test.describe('Retest Creation', () => {

    test('should create a retest from the audit', async ({ page }) => {
      await page.goto(`/audits/${auditId}`);
      // Wait for the sidebar to render
      await expect(page.getByText('Findings')).toBeVisible();

      // Click "Create Retest" button in the sidebar header
      await page.getByRole('button', { name: 'Create Retest' }).click();

      // With only one retest type, the retest is created directly.
      // Wait for navigation to the new retest audit page.
      await page.waitForURL(/\/audits\/[a-f0-9]+/);

      // The sidebar should show the "Retest" chip
      await expect(page.getByText('Retest').first()).toBeVisible();

      // The retest should inherit the finding from the original audit
      await expect(page.getByText('Test SQL Injection Finding')).toBeVisible();
    });
  });
});
