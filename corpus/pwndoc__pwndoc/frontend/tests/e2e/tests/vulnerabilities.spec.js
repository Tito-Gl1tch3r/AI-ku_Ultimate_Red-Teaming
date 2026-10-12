import { test, expect } from './base.js';

const RECOVERY_CATEGORY = 'Critical Findings';

async function openCreateVulnerability(page, category = 'No Category') {
  await page.getByTestId('new-vulnerability-button').click();
  await expect(page.getByText('Select category')).toBeVisible();
  await page.getByRole('listitem').filter({ hasText: new RegExp(`^${category}$`) }).click();
  await expect(page.getByTestId('vulnerability-create-pane')).toBeVisible();
  await expect(page.getByTestId('vulnerability-created-by')).toHaveCount(0);
  await expect(page.getByTestId('create-vulnerability-title')).toBeVisible();
}

async function closeCreateVulnerability(page) {
  await page.getByTestId('create-vulnerability-close').click();
  await expect(page.getByTestId('vulnerability-create-pane')).not.toBeVisible();
}

async function closeEditVulnerability(page) {
  await page.getByTestId('edit-vulnerability-close').click();
  await expect(page.getByTestId('vulnerability-edit-pane')).not.toBeVisible();
}

async function openRecoveryMenu(page) {
  await page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status').click();
}

async function clickRecoveryAction(page, name) {
  await openRecoveryMenu(page);
  if (name instanceof RegExp)
    await page.getByText(name).click();
  else
    await page.getByText(name, { exact: true }).click();
}

async function listDrafts(page) {
  return page.evaluate(async () => {
    const request = indexedDB.open('pwndoc-drafts', 1);
    const db = await new Promise((resolve, reject) => {
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = () => resolve(request.result);
    });

    if (!db.objectStoreNames.contains('drafts')) {
      db.close();
      return [];
    }

    const tx = db.transaction('drafts', 'readonly');
    const drafts = await new Promise((resolve, reject) => {
      const req = tx.objectStore('drafts').getAll();
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve(req.result || []);
    });
    db.close();
    return drafts;
  });
}

async function putDrafts(page, drafts) {
  await page.evaluate(async (drafts) => {
    const request = indexedDB.open('pwndoc-drafts', 1);
    const db = await new Promise((resolve, reject) => {
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains('drafts')) {
          const store = db.createObjectStore('drafts', { keyPath: 'key' });
          store.createIndex('by_userId', 'userId');
          store.createIndex('by_updatedAt', 'updatedAt');
        }
        resolve(db);
      };
    });

    const tx = db.transaction('drafts', 'readwrite');
    const store = tx.objectStore('drafts');
    for (const draft of drafts)
      store.put(draft);

    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }, drafts);
}

async function deleteDrafts(page, predicateSource, arg) {
  await page.evaluate(async ({ predicateSource, arg }) => {
    const predicate = new Function('draft', 'arg', `return (${predicateSource})(draft, arg)`);
    const request = indexedDB.open('pwndoc-drafts', 1);
    const db = await new Promise((resolve, reject) => {
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = () => resolve(request.result);
    });

    if (!db.objectStoreNames.contains('drafts')) {
      db.close();
      return;
    }

    const tx = db.transaction('drafts', 'readwrite');
    const store = tx.objectStore('drafts');
    const drafts = await new Promise((resolve, reject) => {
      const req = store.getAll();
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve(req.result || []);
    });

    for (const draft of drafts) {
      if (predicate(draft, arg))
        store.delete(draft.key);
    }

    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }, { predicateSource, arg });
}

async function createVulnerabilityViaApi(request, title, category = null, overrides = {}) {
  const { detail = {}, ...vulnerabilityOverrides } = overrides;
  const payload = [{
    category,
    status: 0,
    cvssv3: '',
    cvssv4: '',
    priority: '',
    remediationComplexity: '',
    ...vulnerabilityOverrides,
    details: [{
      locale: 'en',
      title,
      vulnType: '',
      description: '',
      observation: '',
      remediation: '',
      references: [],
      customFields: [],
      ...detail,
    }],
  }];

  const createRes = await request.post('/api/vulnerabilities', { data: payload });
  expect(createRes.ok()).toBeTruthy();

  const listRes = await request.get('/api/vulnerabilities');
  const list = await listRes.json();
  const vulnerability = list.datas.find(vuln => vuln.details?.some(detail => detail.title === title));
  expect(vulnerability).toBeTruthy();
  return vulnerability._id;
}

async function openEditVulnerability(page, title) {
  await page.getByTestId('search-vulnerability-title').fill(title);
  const item = page.getByRole('listitem').filter({ hasText: title });
  await expect(item).toBeVisible();
  await item.click();
  await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
  await expect(page.getByTestId('edit-vulnerability-title')).toBeVisible();
}

test.describe('Vulnerabilities Page', () => {

  // Cleanup: remove test vulnerabilities (languages persist from data-setup)
  test.afterAll(async ({ request }) => {
    await request.delete('/api/vulnerabilities');
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/vulnerabilities');
    // Wait for the page to finish loading by checking for a key UI element
    await expect(page.getByTestId('new-vulnerability-button')).toBeVisible();
  });

  test.describe('Page Layout', () => {
    test('should display navigation and page elements', async ({ page }) => {
      // Verify nav items
      await expect(page.getByRole('listitem').filter({ hasText: 'Audits' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'Vulnerabilities' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'Data' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'Settings' })).toBeVisible();

      // Verify language selector is present
      await expect(page.getByLabel('Language')).toBeVisible();

      // Verify status filter chips
      await expect(page.getByTestId('status-filter-all')).toBeVisible();
      await expect(page.getByTestId('status-filter-valid')).toBeVisible();
      await expect(page.getByTestId('status-filter-new')).toBeVisible();
      await expect(page.getByTestId('status-filter-updates')).toBeVisible();

      // Verify "New Vulnerability" dropdown button
      await expect(page.getByTestId('new-vulnerability-button')).toBeVisible();

      // Verify "Merge Vulnerabilities" button
      await expect(page.getByRole('button', { name: 'Merge Vulnerabilities' })).toBeVisible();
    });

    test('should show empty list when no vulnerabilities exist', async ({ page }) => {
      await expect(page.getByText('No matching records found')).toBeVisible({ timeout: 10000 });
    });

    test('should show the empty detail pane placeholder when nothing is selected', async ({ page }) => {
      await expect(page.getByTestId('vulnerability-empty-state')).toBeVisible();
    });
  });

  test.describe('CRUD Operations', () => {
    test('should create a new vulnerability', async ({ page }) => {
      // Click "New Vulnerability" dropdown and wait for menu to appear
      await page.getByTestId('new-vulnerability-button').click();
      await expect(page.getByText('Select category')).toBeVisible();
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();

      // Wait for the create pane to open and fill in the title
      await expect(page.getByTestId('vulnerability-create-pane')).toBeVisible();
      await page.getByTestId('create-vulnerability-title').fill('Test SQL Injection');

      // Save through the same keyboard path used by the audit editors.
      await page.keyboard.press('Control+s');

      await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      // Verify the vulnerability appears in the list
      await expect(page.getByRole('listitem').filter({ hasText: 'Test SQL Injection' })).toBeVisible();
    });

    test('should edit an existing vulnerability', async ({ page }) => {
      // First create a vulnerability to edit
      await page.getByTestId('new-vulnerability-button').click();
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();
      await page.getByTestId('create-vulnerability-title').fill('Vuln To Edit');
      await page.getByTestId('save-vulnerability-button').click();
      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      // Click the vulnerability in the list to open the edit pane
      const item = page.getByRole('listitem').filter({ hasText: 'Vuln To Edit' });
      await item.click();

      // The edit pane should appear
      await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
      await expect(page.getByText(/Edit Vulnerability/)).not.toBeVisible();

      // Clear and update the title
      await page.getByTestId('edit-vulnerability-title').fill('Vuln Edited Successfully');

      // Click Update button
      await page.getByTestId('save-vulnerability-button').click();

      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      // Verify the updated title appears in the list
      await expect(page.getByRole('listitem').filter({ hasText: 'Vuln Edited Successfully' })).toBeVisible();

      // Verify old title is gone
      await expect(page.getByRole('listitem').filter({ hasText: 'Vuln To Edit' })).not.toBeVisible();
    });

    test('should delete a vulnerability', async ({ page }) => {
      // First create a vulnerability to delete
      await page.getByTestId('new-vulnerability-button').click();
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();
      await page.getByTestId('create-vulnerability-title').fill('Vuln To Delete');
      await page.getByTestId('save-vulnerability-button').click();
      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      // Open the vulnerability and click the delete button in the pane header
      const item = page.getByRole('listitem').filter({ hasText: 'Vuln To Delete' });
      await item.click();
      await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
      await page.getByTestId('delete-vulnerability-button').click();

      // Confirm deletion in the dialog
      await expect(page.getByText('Vulnerability will be permanently deleted')).toBeVisible();
      await page.getByRole('button', { name: 'Confirm' }).click();

      // Verify success notification
      await expect(page.getByText('Vulnerability deleted successfully')).toBeVisible();

      // Verify the vulnerability is no longer in the list
      await expect(page.getByRole('listitem').filter({ hasText: 'Vuln To Delete' })).not.toBeVisible();
    });
  });

  test.describe('Quality Assurance', () => {
    test('should run built-in checks without AI provider credentials', async ({ page, request }) => {
      const title = `E2E Built-in QA ${Date.now()}`;
      await createVulnerabilityViaApi(request, title);
      await page.reload();
      await openEditVulnerability(page, title);

      await page.getByTestId('vulnerability-qa-toggle').click();
      await expect(page.getByText('QA Review', { exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Run Built-in Checks' }).click();

      await expect(page.getByText('Missing description', { exact: true })).toBeVisible();
      await expect(page.getByText('Missing remediation', { exact: true })).toBeVisible();
      await expect(page.getByText('Missing observation', { exact: true })).toBeVisible();
    });

    test('should run catalog built-in checks and keep the dock open while navigating to a result', async ({ page, request }) => {
      const title = `E2E Catalog QA ${Date.now()}`;
      await createVulnerabilityViaApi(request, title);
      await page.reload();

      await page.getByTestId('vulnerability-qa-all-toggle').click();
      const dock = page.getByTestId('vulnerability-qa-dock');
      await expect(dock.getByText('Vulnerability Database QA Review')).toBeVisible();
      await dock.getByRole('button', { name: /^(Run Built-in Checks|Run again Built-in checks)$/i }).click();

      await expect(dock.getByText(/Reviewed \d+ vulnerabilities for the selected language\./)).toBeVisible();
      await dock.getByTestId('qa-text-filter').fill(title);
      const goToVulnerability = dock.getByRole('listitem').filter({ hasText: title })
        .getByRole('button', { name: 'Go to vulnerability' });
      await expect(goToVulnerability).toBeVisible();
      await goToVulnerability.click();

      await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(title);
      await expect(dock).toBeVisible();
    });
  });

  test.describe('Update proposals', () => {
    test('should compare and dismiss a proposal from the review modal', async ({ page, request }) => {
      const title = `E2E Proposal ${Date.now()}`;
      await createVulnerabilityViaApi(request, title, null, {
        detail: { description: '<p>Current description</p>' },
      });
      const proposal = await request.post('/api/vulnerabilities/finding/en', {
        data: { title, description: '<p>Proposed description</p>' },
      });
      expect(proposal.ok()).toBeTruthy();
      await page.reload();
      await openEditVulnerability(page, title);

      await page.getByTestId('vulnerability-updates-button').click();
      const modal = page.getByRole('dialog').filter({ hasText: 'Review vulnerability proposals' });
      await expect(modal.getByText('Current version · English')).toBeVisible();
      await expect(modal.getByText(/Proposed version/)).toBeVisible();
      await expect(modal.getByTestId('updates-current-title')).toHaveValue(title);
      await expect(modal.getByTestId('vulnerability-update-proposal').getByText('Proposed description')).toBeVisible();

      await modal.getByTestId('dismiss-vulnerability-update-button').click();
      const confirmation = page.getByRole('dialog').filter({ hasText: 'Confirm dismissal' });
      await confirmation.getByRole('button', { name: 'Confirm' }).click();
      await expect(page.getByText('Update proposals dismissed successfully')).toBeVisible();
      await expect(page.getByTestId('vulnerability-updates-button')).not.toBeVisible();
    });
  });

  test.describe('Assisted writing', () => {
    test('should preview and apply a generated description before saving it', async ({ page, request }) => {
      const title = `E2E AI Description ${Date.now()}`;
      const generated = 'Generated vulnerability description';
      const settingsResponse = await request.get('/api/settings');
      expect(settingsResponse.ok()).toBeTruthy();
      const settings = (await settingsResponse.json()).datas;
      const aiWasEnabled = settings.ai.public.enabled;
      settings.ai.public.enabled = true;
      expect((await request.put('/api/settings', { data: settings })).ok()).toBeTruthy();

      try {
        await createVulnerabilityViaApi(request, title);
        let generatePayload;
        await page.route('**/api/ai/generate', async (route) => {
          generatePayload = route.request().postDataJSON();
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `event: done\ndata: ${JSON.stringify({ draft: `<p>${generated}</p>`, reply: 'Draft ready' })}\n\n`,
          });
        });
        await page.reload();
        await openEditVulnerability(page, title);

        const pane = page.getByTestId('vulnerability-edit-pane');
        await pane.getByTestId('editor-ai-action').first().click();
        const drawer = page.locator('.ai-chat-drawer__panel');
        await expect(drawer.getByText('AI - Description')).toBeVisible();
        await expect(drawer.getByText('How can I help?')).toBeVisible();
        await expect(drawer.getByText('OpenAI', { exact: true })).toBeVisible();
        await drawer.getByPlaceholder('Ask anything').fill('Write the description');
        await drawer.getByRole('button', { name: 'Send' }).click();

        await expect(drawer.getByText('Draft ready')).toBeVisible();
        await drawer.getByRole('button', { name: 'Preview changes' }).click();
        await expect(drawer.getByRole('button', { name: 'Original response' })).toBeVisible();
        await drawer.getByRole('button', { name: 'Apply to field' }).click();
        expect(generatePayload).toMatchObject({ entityType: 'finding', field: 'description', locale: 'en' });
        await drawer.getByRole('button').first().click();

        await expect(pane.getByText(generated, { exact: true })).toBeVisible();
        await pane.getByTestId('save-vulnerability-button').click();
        await expect(pane.getByTestId('save-vulnerability-button')).toContainText('Saved');
        await page.reload();
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(title);
        await expect(page.getByTestId('vulnerability-edit-pane').getByText(generated, { exact: true })).toBeVisible();
      }
      finally {
        settings.ai.public.enabled = aiWasEnabled;
        expect((await request.put('/api/settings', { data: settings })).ok()).toBeTruthy();
      }
    });
  });

  test.describe('Search and Filter', () => {
    test('should combine status and advanced filters, clear them, and reverse title sort', async ({ page, request }) => {
      const runId = `E2E Browse ${Date.now()}`;
      const titles = {
        alpha: `${runId} A Valid`,
        beta: `${runId} B Valid`,
        created: `${runId} C New`,
        updated: `${runId} D Updates`,
      };
      await createVulnerabilityViaApi(request, titles.alpha, 'Critical Findings', {
        cvssv3: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
        detail: { vulnType: 'Web Application' },
      });
      await createVulnerabilityViaApi(request, titles.beta, 'Minor Findings', {
        detail: { vulnType: 'Network' },
      });
      const created = await request.post('/api/vulnerabilities/finding/en', {
        data: { title: titles.created, category: 'Critical Findings', vulnType: 'Network' },
      });
      expect(created.ok()).toBeTruthy();
      await createVulnerabilityViaApi(request, titles.updated, 'Critical Findings', {
        detail: { vulnType: 'Network' },
      });
      const updated = await request.post('/api/vulnerabilities/finding/en', {
        data: { title: titles.updated, category: 'Critical Findings', vulnType: 'Network', description: 'Changed' },
      });
      expect(updated.ok()).toBeTruthy();
      await page.reload();

      const search = page.getByTestId('search-vulnerability-title');
      await search.fill(runId);
      const item = (title) => page.getByRole('listitem').filter({ hasText: title });
      for (const title of Object.values(titles))
        await expect(item(title)).toBeVisible();

      await page.getByRole('button', { name: 'Filters' }).click();
      await page.getByLabel('Critical Findings').check();
      await page.getByLabel('Web Application').check();
      await expect(item(titles.alpha)).toBeVisible();
      await expect(item(titles.updated)).not.toBeVisible();
      await page.getByRole('button', { name: 'Clear all' }).click();
      for (const title of Object.values(titles))
        await expect(item(title)).toBeVisible();
      await page.keyboard.press('Escape');

      await page.getByTestId('status-filter-new').click();
      await expect(item(titles.created)).toBeVisible();
      await expect(item(titles.alpha)).not.toBeVisible();
      await page.getByTestId('status-filter-updates').click();
      await expect(item(titles.updated)).toBeVisible();
      await expect(item(titles.created)).not.toBeVisible();
      await page.getByTestId('status-filter-all').click();

      await page.getByTestId('vulnerability-sort').click();
      await page.getByRole('listitem').filter({ hasText: /^Title/ }).click();
      await expect.poll(async () => (await page.getByRole('listitem').filter({ hasText: runId }).first().innerText()))
        .toContain(titles.updated);
    });

    test('should filter vulnerabilities by title search', async ({ page }) => {
      // Create two vulnerabilities with different titles
      await page.getByTestId('new-vulnerability-button').click();
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();
      await page.getByTestId('create-vulnerability-title').fill('XSS Reflected');
      await page.getByTestId('save-vulnerability-button').click();
      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      await page.getByTestId('new-vulnerability-button').click();
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();
      await page.getByTestId('create-vulnerability-title').fill('CSRF Token Missing');
      await page.getByTestId('save-vulnerability-button').click();
      await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');

      // Both should be visible initially
      await expect(page.getByRole('listitem').filter({ hasText: 'XSS Reflected' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'CSRF Token Missing' })).toBeVisible();

      // Type in the sidebar search field
      const searchInput = page.getByTestId('search-vulnerability-title');
      await searchInput.fill('xss');

      // XSS should still be visible, CSRF should be filtered out
      await expect(page.getByRole('listitem').filter({ hasText: 'XSS Reflected' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'CSRF Token Missing' })).not.toBeVisible();

      // Clear search to see all again
      await searchInput.clear();
      await expect(page.getByRole('listitem').filter({ hasText: 'XSS Reflected' })).toBeVisible();
      await expect(page.getByRole('listitem').filter({ hasText: 'CSRF Token Missing' })).toBeVisible();
    });
  });

  test.describe('Validation', () => {
    test('should show error when creating vulnerability without title', async ({ page }) => {
      // Click "New Vulnerability" dropdown
      await page.getByTestId('new-vulnerability-button').click();

      // Select "No Category"
      await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();

      // Verify create pane opened
      await expect(page.getByTestId('vulnerability-create-pane')).toBeVisible();
      await expect(page.getByTestId('create-vulnerability-title')).toBeVisible();

      // Click Create without filling the title
      await page.getByTestId('save-vulnerability-button').click();

      // Verify error message for missing title
      await expect(page.getByText('Title required')).toBeVisible();
    });
  });

  test.describe('Draft Recovery', () => {
    test('should recover new vulnerability drafts independently by category and support revert/restore', async ({ page }) => {
      const runId = `E2E Recovery ${Date.now()}`;
      const noCategoryDraftTitle = `${runId} No Category Draft`;
      const savedNoCategoryTitle = `${runId} No Category Saved`;
      const categoryDraftTitle = `${runId} Category Draft`;
      const createRefKeys = ['_new:none', `_new:${RECOVERY_CATEGORY}`];
      const existingDrafts = await listDrafts(page);
      const backedUpDrafts = existingDrafts.filter(draft =>
        draft.scope === 'vuln-modal-create' && createRefKeys.includes(draft.refKey)
      );

      await deleteDrafts(
        page,
        '(draft, refKeys) => draft.scope === "vuln-modal-create" && refKeys.includes(draft.refKey)',
        createRefKeys
      );

      try {
        await openCreateVulnerability(page);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).not.toBeVisible();
        await page.getByTestId('create-vulnerability-title').fill(noCategoryDraftTitle);
        await closeCreateVulnerability(page);

        await page.getByTestId('new-vulnerability-button').click();
        await expect(page.getByText('Select category')).toBeVisible();
        await expect(page.getByTestId('create-vulnerability-draft-badge-none')).toBeVisible();
        await page.getByRole('listitem').filter({ hasText: /^No Category$/ }).click();
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue(noCategoryDraftTitle);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).toBeVisible();

        await clickRecoveryAction(page, /^View changes/);
        const diffDialog = page.getByRole('dialog').filter({ hasText: 'Review the differences between your recovered changes and the last saved version.' });
        await expect(diffDialog.getByText('Recovered changes', { exact: true })).toBeVisible();
        await diffDialog.getByRole('button').first().click();

        await clickRecoveryAction(page, 'Revert to saved version');
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue('');

        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).toBeVisible();
        await clickRecoveryAction(page, 'Restore recovered changes');
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue(noCategoryDraftTitle);

        await page.getByTestId('create-vulnerability-title').fill(savedNoCategoryTitle);
        await expect.poll(async () => {
          const drafts = await listDrafts(page);
          return drafts.find(draft =>
            draft.scope === 'vuln-modal-create' && draft.refKey === '_new:none'
          )?.data?.details?.some(detail => detail.title === savedNoCategoryTitle) || false;
        }).toBe(true);
        await page.getByTestId('save-vulnerability-button').click();
        await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');
        await page.getByTestId('new-vulnerability-button').click();
        await expect(page.getByText('Select category')).toBeVisible();
        await expect(page.getByTestId('create-vulnerability-draft-badge-none')).not.toBeVisible();
        await page.keyboard.press('Escape');

        await expect.poll(async () => {
          const drafts = await listDrafts(page);
          return drafts.some(draft => draft.scope === 'vuln-modal-create' && draft.refKey === '_new:none');
        }).toBe(false);

        await openCreateVulnerability(page, RECOVERY_CATEGORY);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).not.toBeVisible();
        await page.getByTestId('create-vulnerability-title').fill(categoryDraftTitle);
        await closeCreateVulnerability(page);

        await openCreateVulnerability(page, RECOVERY_CATEGORY);
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue(categoryDraftTitle);
        await closeCreateVulnerability(page);

        await openCreateVulnerability(page);
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue('');
        await closeCreateVulnerability(page);

        await openCreateVulnerability(page, RECOVERY_CATEGORY);
        await expect(page.getByTestId('create-vulnerability-title')).toHaveValue(categoryDraftTitle);
        await closeCreateVulnerability(page);
      }
      finally {
        await deleteDrafts(
          page,
          '(draft, refKeys) => draft.scope === "vuln-modal-create" && refKeys.includes(draft.refKey)',
          createRefKeys
        );
        await putDrafts(page, backedUpDrafts);
      }
    });

    test('should isolate edit drafts per vulnerability and clear only the saved draft', async ({ page, request }) => {
      const runId = `E2E Recovery ${Date.now()}`;
      const editABase = `${runId} Edit A Base`;
      const editBBase = `${runId} Edit B Base`;
      const editADraft = `${runId} Edit A Draft`;
      const editBDraft = `${runId} Edit B Draft`;
      const editAId = await createVulnerabilityViaApi(request, editABase);
      const editBId = await createVulnerabilityViaApi(request, editBBase, RECOVERY_CATEGORY);

      await page.reload();
      await expect(page.getByTestId('new-vulnerability-button')).toBeVisible();

      try {
        await openEditVulnerability(page, editABase);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).not.toBeVisible();
        await page.getByTestId('edit-vulnerability-title').fill(editADraft);
        await closeEditVulnerability(page);
        await expect(page.getByTestId(`vulnerability-draft-badge-${editAId}`)).toBeVisible();

        await openEditVulnerability(page, editABase);
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(editADraft);
        await closeEditVulnerability(page);

        await openEditVulnerability(page, editBBase);
        await page.getByTestId('edit-vulnerability-title').fill(editBDraft);
        await closeEditVulnerability(page);

        await openEditVulnerability(page, editBBase);
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(editBDraft);
        await closeEditVulnerability(page);

        await openEditVulnerability(page, editABase);
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(editADraft);

        await page.getByTestId('save-vulnerability-button').click();
        await expect(page.getByTestId('save-vulnerability-button')).toContainText('Saved');
        await expect(page.getByTestId(`vulnerability-draft-badge-${editAId}`)).not.toBeVisible();

        await expect.poll(async () => {
          const drafts = await listDrafts(page);
          return {
            editAExists: drafts.some(draft => draft.scope === 'vuln-modal-edit' && draft.refKey === editAId),
            editBExists: drafts.some(draft => draft.scope === 'vuln-modal-edit' && draft.refKey === editBId),
          };
        }).toEqual({ editAExists: false, editBExists: true });

        await openEditVulnerability(page, editADraft);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).not.toBeVisible();
        await closeEditVulnerability(page);

        await openEditVulnerability(page, editBBase);
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(editBDraft);
        await expect(page.getByTestId('vulnerability-detail-pane').getByTestId('draft-recovery-status')).toBeVisible();
        await closeEditVulnerability(page);
      }
      finally {
        await deleteDrafts(
          page,
          '(draft, refKeys) => draft.scope === "vuln-modal-edit" && refKeys.includes(draft.refKey)',
          [editAId, editBId]
        );
      }
    });
  });

  test.describe('URL navigation', () => {
    test('reflects the open vulnerability in the URL, supports deep-linking and history', async ({ page, request }) => {
      const title = `URL Nav ${Date.now()}`;
      const id = await createVulnerabilityViaApi(request, title);
      try {
        await page.goto('/vulnerabilities');
        await openEditVulnerability(page, title);

        // The open vulnerability is reflected in the URL.
        await expect(page).toHaveURL(new RegExp(`/vulnerabilities/${id}$`));

        // Deep-link: reloading the detail URL reopens that vulnerability's pane.
        await page.reload();
        await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
        await expect(page.getByTestId('edit-vulnerability-title')).toHaveValue(title);

        // Closing the pane resets the URL to the base list.
        await page.getByTestId('edit-vulnerability-close').click();
        await expect(page).toHaveURL(/\/vulnerabilities$/);
        await expect(page.getByTestId('vulnerability-empty-state')).toBeVisible();

        // Browser back navigation reopens the previously viewed vulnerability.
        await page.goBack();
        await expect(page).toHaveURL(new RegExp(`/vulnerabilities/${id}$`));
        await expect(page.getByTestId('vulnerability-edit-pane')).toBeVisible();
      }
      finally {
        await request.delete(`/api/vulnerabilities/${id}`);
      }
    });
  });
});
