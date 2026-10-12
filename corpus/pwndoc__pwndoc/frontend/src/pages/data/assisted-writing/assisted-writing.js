import { Notify, Dialog } from 'quasar';
import draggable from 'vuedraggable';
import DataService from '@/services/data';
import { useUserStore } from '@/stores/user';
import { $t } from '@/boot/i18n';
import AiFieldHelper from '@/services/ai-field-helper';
import {
    defaultMarkdownInstructions,
    serializeMarkdownInstructions
} from '@/pages/data/ai-integration-shared';

const OUTPUT_TYPE_LABEL_KEYS = {
    html: 'aiIntegration.prompts.outputTypeHtml',
    array: 'aiIntegration.prompts.outputTypeList',
    text: 'aiIntegration.prompts.outputTypeText'
};

const CUSTOM_FIELD_LABEL_PREFIX = /^(Finding|Section) Custom Field:\s*/;

// Derived from the context objects services/ai-field-helper.js actually builds
// (buildFindingAiContext / buildSectionAiContext), rather than a hand-kept copy
// of their keys that could silently drift out of sync.
const promptVariablesFor = (contextBuilder) => Object.keys(contextBuilder({})).filter((key) => key !== 'customFields');
const FINDING_PROMPT_VARIABLES = promptVariablesFor(AiFieldHelper.buildFindingAiContext);
const SECTION_PROMPT_VARIABLES = promptVariablesFor(AiFieldHelper.buildSectionAiContext);

// Drives the three category branches of the prompt tree (Findings, Vulnerabilities,
// Sections). Each has an "All categories" leaf keyed `<key>:all` plus one leaf per
// custom-field category under `catPrefix`; Findings additionally has a "Built-in
// fields" leaf since findings (unlike vulnerabilities/sections) have AI-assisted
// built-in fields of their own.
const TREE_PARENT_CONFIGS = [
    {
        key: 'findings',
        labelKey: 'aiIntegration.prompts.nodeFindings',
        catPrefix: 'findings:cat:',
        extraLeaves: [
            { key: 'findings:builtin', labelKey: 'aiIntegration.prompts.nodeBuiltinFields' },
            { key: 'findings:all', labelKey: 'aiIntegration.prompts.nodeAllCategories' }
        ]
    },
    {
        key: 'vulnerabilities',
        labelKey: 'aiIntegration.prompts.nodeVulnerabilities',
        catPrefix: 'vulnerabilities:cat:',
        extraLeaves: [
            { key: 'vulnerabilities:all', labelKey: 'aiIntegration.prompts.nodeAllCategories' }
        ]
    },
    {
        key: 'sections',
        labelKey: 'aiIntegration.prompts.nodeSections',
        catPrefix: 'sections:sub:',
        extraLeaves: [
            { key: 'sections:all', labelKey: 'aiIntegration.prompts.nodeAllSections' }
        ]
    }
];
const TREE_PARENT_KEYS = TREE_PARENT_CONFIGS.map((config) => config.key);

const userStore = useUserStore();

const toMappingKey = (mapping) => `${mapping.entityType}:${mapping.fieldKey}`;

// Leaf node of the navigation tree a field prompt belongs to.
const mappingNodeKey = (mapping) => {
    if (mapping.entityType === 'section')
        return mapping.customFieldDisplaySub ? `sections:sub:${mapping.customFieldDisplaySub}` : 'sections:all';

    if (mapping.source === 'builtin')
        return 'findings:builtin';

    if (mapping.customFieldDisplay === 'vulnerability')
        return mapping.customFieldDisplaySub ? `vulnerabilities:cat:${mapping.customFieldDisplaySub}` : 'vulnerabilities:all';

    return mapping.customFieldDisplaySub ? `findings:cat:${mapping.customFieldDisplaySub}` : 'findings:all';
};

const serializeGlobalPrompts = (prompts = []) => {
    // Array order is meaningful: the AI chat drawer lists generic prompts in stored order.
    return prompts.map((entry) => ({
        id: String(entry.id || ''),
        label: String(entry.label || ''),
        prompt: String(entry.prompt || ''),
        enabled: entry.enabled !== false
    }));
};

const createGlobalPromptId = () => {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function')
        return crypto.randomUUID();
    return `global-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default {
    components: {
        draggable
    },

    beforeRouteLeave(to, from, next) {
        if (this.editorDirty || this.hasGuidelineChanges) {
            Dialog.create({
                title: $t('msg.thereAreUnsavedChanges'),
                message: $t('msg.doYouWantToLeave'),
                ok: { label: $t('btn.confirm'), color: 'negative' },
                cancel: { label: $t('btn.cancel'), color: 'white' },
                focus: 'cancel'
            })
            .onOk(() => next());
            return;
        }

        next();
    },

    data: () => {
        return {
            loading: true,
            savingPrompts: false,
            savingEditor: false,
            savingGuidelines: false,
            canEditPrompts: userStore.isAllowed('ai:prompts:update'),
            canEditGuidelines: userStore.isAllowed('ai:redaction-guidelines:update'),
            canReadPrompts: userStore.isAllowed('ai:prompts:read'),
            canReadGuidelines: userStore.isAllowed('ai:redaction-guidelines:read'),
            aiEnabled: true,
            promptMappings: [],
            globalPrompts: [],
            redactionGuidelines: defaultMarkdownInstructions(),
            writingTab: 'prompts',
            promptToggleSaveKey: null,
            promptToggleSaveState: null,
            promptToggleSaveTimer: null,
            treeFilter: '',
            tableFilter: '',
            selectedNode: 'generic',
            expandedNodes: [...TREE_PARENT_KEYS],
            selectedGenericIds: [],
            editor: null,
            fieldTablePagination: {
                rowsPerPage: 0
            },
            orig: {
                redactionGuidelines: serializeMarkdownInstructions()
            }
        };
    },

    mounted: function() {
        this.getAiIntegration();
    },

    beforeUnmount: function() {
        if (this.promptToggleSaveTimer)
            clearTimeout(this.promptToggleSaveTimer);
    },

    watch: {
        treeFilter: function(value) {
            if (String(value || '').trim())
                this.expandedNodes = [...TREE_PARENT_KEYS];
        },

        selectedNode: function() {
            this.tableFilter = '';
            this.selectedGenericIds = [];
        }
    },

    computed: {
        pageTitle: function() {
            return this.$t('aiIntegration.pageTitleWriting');
        },

        canViewPage: function() {
            return this.canReadPrompts || this.canReadGuidelines;
        },

        // Tree leaves with total field count.
        promptTreeLeaves: function() {
            const leaves = new Map();

            this.promptMappings.forEach((mapping) => {
                const key = mappingNodeKey(mapping);
                leaves.set(key, (leaves.get(key) || 0) + 1);
            });

            return leaves;
        },

        // The tree search only matches node/category names, not the fields they contain.
        promptTreeNodes: function() {
            const filterText = String(this.treeFilter || '').trim().toLowerCase();
            const leaves = this.promptTreeLeaves;

            const labelMatches = (label) => !filterText || String(label).toLowerCase().includes(filterText);

            // showAll bypasses the filter for a node's children once its own parent
            // label already matched - the whole matched branch is shown.
            const leafNode = (key, label, showAll) => {
                const count = leaves.get(key);
                if (!count)
                    return null;
                if (!showAll && !labelMatches(label))
                    return null;
                return { key: key, label: label, count: count };
            };

            const categoryLeafNodes = (prefix, showAll) => {
                return Array.from(leaves.keys())
                .filter((key) => key.startsWith(prefix))
                .map((key) => ({ key: key, label: key.slice(prefix.length) }))
                .sort((a, b) => a.label.localeCompare(b.label))
                .map((entry) => leafNode(entry.key, entry.label, showAll))
                .filter(Boolean);
            };

            const parentNode = (key, label, children) => {
                if (children.length === 0)
                    return null;
                return {
                    key: key,
                    label: label,
                    count: children.reduce((total, child) => total + child.count, 0),
                    children: children
                };
            };

            const nodes = [];

            const genericLabel = this.$t('aiIntegration.prompts.genericPrompts');
            if (labelMatches(genericLabel)) {
                nodes.push({
                    key: 'generic',
                    label: genericLabel,
                    count: this.globalPrompts.length
                });
            }

            TREE_PARENT_CONFIGS.forEach((config) => {
                const label = this.$t(config.labelKey);
                const showAll = labelMatches(label);
                const node = parentNode(config.key, label, [
                    ...config.extraLeaves.map((leaf) => leafNode(leaf.key, this.$t(leaf.labelKey), showAll)),
                    ...categoryLeafNodes(config.catPrefix, showAll)
                ].filter(Boolean));

                if (node)
                    nodes.push(node);
            });

            return nodes;
        },

        isGenericNodeSelected: function() {
            return this.selectedNode === 'generic';
        },

        selectedNodeMappings: function() {
            const key = this.selectedNode;
            if (!key || key === 'generic')
                return [];

            return this.promptMappings.filter((mapping) => {
                const nodeKey = mappingNodeKey(mapping);
                return nodeKey === key || nodeKey.startsWith(`${key}:`);
            });
        },

        fieldTableRows: function() {
            const filterText = this.tableFilter.trim().toLowerCase();
            if (!filterText)
                return this.selectedNodeMappings;

            return this.selectedNodeMappings.filter((mapping) => {
                return this.fieldDisplayLabel(mapping).toLowerCase().includes(filterText);
            });
        },

        fieldTableColumns: function() {
            return [
                { name: 'field', label: this.$t('aiIntegration.prompts.columnField'), field: (row) => this.fieldDisplayLabel(row), align: 'left', sortable: true },
                { name: 'enabled', label: this.$t('aiIntegration.prompts.aiAssist'), field: 'enabled', align: 'center' },
                { name: 'preview', label: this.$t('aiIntegration.prompts.columnPrompt'), field: 'prompt', align: 'left' }
            ];
        },

        filteredGenericPrompts: function() {
            const filterText = this.tableFilter.trim().toLowerCase();
            if (!filterText)
                return this.globalPrompts;

            return this.globalPrompts.filter((entry) => {
                return String(entry.label || '').toLowerCase().includes(filterText) ||
                    String(entry.prompt || '').toLowerCase().includes(filterText);
            });
        },

        canReorderGeneric: function() {
            return this.canEditPrompts && !this.tableFilter.trim() && this.globalPrompts.length > 1;
        },

        genericDragList: {
            get: function() {
                return this.filteredGenericPrompts;
            },
            set: function(list) {
                this.persistGenericOrder(list);
            }
        },

        editorSourceMapping: function() {
            if (this.editor?.kind !== 'field')
                return null;
            return this.promptMappings.find((mapping) => toMappingKey(mapping) === this.editor.mappingKey) || null;
        },

        editorSourceGeneric: function() {
            if (this.editor?.kind !== 'generic' || this.editor.isNew)
                return null;
            return this.globalPrompts.find((entry) => entry.id === this.editor.id) || null;
        },

        editorDirty: function() {
            if (!this.editor)
                return false;

            if (this.editor.kind === 'field') {
                const source = this.editorSourceMapping;
                if (!source)
                    return false;
                return this.editor.enabled !== (source.enabled !== false) || this.editor.prompt !== String(source.prompt || '');
            }

            if (this.editor.isNew)
                return !!(this.editor.label.trim() || this.editor.prompt.trim());

            const source = this.editorSourceGeneric;
            if (!source)
                return false;
            return this.editor.label !== String(source.label || '') ||
                this.editor.prompt !== String(source.prompt || '') ||
                this.editor.enabled !== (source.enabled !== false);
        },

        editorCanSave: function() {
            if (!this.canEditPrompts || !this.editor)
                return false;
            if (this.editor.kind === 'generic')
                return this.editorDirty && !!this.editor.label.trim() && !!this.editor.prompt.trim();
            return this.editorDirty;
        },

        editorBreadcrumbs: function() {
            if (!this.editor)
                return [];

            if (this.editor.kind === 'generic') {
                return [
                    this.$t('aiIntegration.prompts.genericPrompts'),
                    this.editor.isNew ? this.$t('aiIntegration.prompts.newPrompt') : this.editor.label || this.$t('aiIntegration.prompts.newPrompt')
                ];
            }

            const mapping = this.editorSourceMapping;
            if (!mapping)
                return [];

            const nodeKey = mappingNodeKey(mapping);
            const crumbs = [];

            if (nodeKey.startsWith('findings'))
                crumbs.push(this.$t('aiIntegration.prompts.nodeFindings'));
            else if (nodeKey.startsWith('vulnerabilities'))
                crumbs.push(this.$t('aiIntegration.prompts.nodeVulnerabilities'));
            else
                crumbs.push(this.$t('aiIntegration.prompts.nodeSections'));

            if (nodeKey === 'findings:builtin')
                crumbs.push(this.$t('aiIntegration.prompts.nodeBuiltinFields'));
            else if (nodeKey === 'findings:all' || nodeKey === 'vulnerabilities:all')
                crumbs.push(this.$t('aiIntegration.prompts.nodeAllCategories'));
            else if (nodeKey === 'sections:all')
                crumbs.push(this.$t('aiIntegration.prompts.nodeAllSections'));
            else
                crumbs.push(nodeKey.replace(/^(findings:cat:|vulnerabilities:cat:|sections:sub:)/, ''));

            crumbs.push(this.fieldDisplayLabel(mapping));
            return crumbs;
        },

        editorPromptVariables: function() {
            const mapping = this.editorSourceMapping;
            if (!mapping)
                return [];
            return mapping.entityType === 'section' ? SECTION_PROMPT_VARIABLES : FINDING_PROMPT_VARIABLES;
        },

        hasGuidelineChanges: function() {
            return JSON.stringify(
                serializeMarkdownInstructions(this.redactionGuidelines)
            ) !== JSON.stringify(this.orig.redactionGuidelines);
        }
    },

    methods: {
        applyPayload: function(payload, options = {}) {
            const promptsOnly = options.only === 'prompts';

            this.aiEnabled = payload.aiEnabled !== false;

            if (Array.isArray(payload.promptMappings)) {
                this.promptMappings = payload.promptMappings.map((mapping) => ({
                    ...mapping,
                    entityType: String(mapping.entityType || ''),
                    enabled: mapping.enabled !== false,
                    prompt: String(mapping.prompt || '')
                }));
            }

            if (Array.isArray(payload.globalPrompts)) {
                this.globalPrompts = serializeGlobalPrompts(payload.globalPrompts);
                const validIds = new Set(this.globalPrompts.map((entry) => entry.id));
                this.selectedGenericIds = this.selectedGenericIds.filter((id) => validIds.has(id));
            }

            // Prompt saves return the full admin payload; skip the guidelines section so an
            // in-progress guidelines edit is not silently overwritten.
            if (promptsOnly)
                return;

            if (payload.redactionGuidelines) {
                const guidelines = payload.redactionGuidelines;
                this.redactionGuidelines = {
                    content: String(guidelines.content || '')
                };
                this.orig.redactionGuidelines = serializeMarkdownInstructions(this.redactionGuidelines);
            }
        },

        getAiIntegration: function() {
            this.loading = true;
            DataService.getAiIntegration()
            .then((data) => {
                this.applyPayload(data.data.datas || {});
            })
            .catch((err) => {
                Notify.create({
                    message: err.response?.data?.datas || this.$t('aiIntegration.loadFailed'),
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .finally(() => {
                this.loading = false;
                if (!this.canReadPrompts && this.canReadGuidelines)
                    this.writingTab = 'guidelines';
            });
        },

        notifySuccess: function(message) {
            Notify.create({
                message: message,
                color: 'positive',
                textColor: 'white',
                position: 'top-right'
            });
        },

        notifySaveError: function(err) {
            Notify.create({
                message: err.response?.data?.datas || this.$t('aiIntegration.prompts.saveFailed'),
                color: 'negative',
                textColor: 'white',
                position: 'top-right'
            });
        },

        fieldDisplayLabel: function(mapping) {
            return String(mapping.fieldLabel || '').replace(CUSTOM_FIELD_LABEL_PREFIX, '');
        },

        variableToken: function(variable) {
            return `{${variable}}`;
        },

        outputTypeLabel: function(outputType) {
            const key = OUTPUT_TYPE_LABEL_KEYS[outputType];
            return key ? this.$t(key) : outputType;
        },

        /* ===== Immediate persistence helpers ===== */

        clearPromptToggleSaveStatus: function() {
            if (this.promptToggleSaveTimer)
                clearTimeout(this.promptToggleSaveTimer);
            this.promptToggleSaveTimer = null;
            this.promptToggleSaveKey = null;
            this.promptToggleSaveState = null;
        },

        startPromptToggleSaveStatus: function(key) {
            this.clearPromptToggleSaveStatus();
            this.promptToggleSaveKey = key;
            this.promptToggleSaveState = 'saving';
        },

        finishPromptToggleSaveStatus: function() {
            this.promptToggleSaveState = 'saved';
            this.promptToggleSaveTimer = setTimeout(() => {
                this.clearPromptToggleSaveStatus();
            }, 2000);
        },

        updatePrompts: function(payload, successMessage, options = {}) {
            this.savingPrompts = true;
            return DataService.updateAiIntegration(payload)
            .then((data) => {
                // skipApply: after a drag-reorder the optimistic list already matches the
                // server; re-replacing the array fights sortable's DOM move and renders
                // the old order until reload.
                if (!options.skipApply)
                    this.applyPayload(data.data.datas || {}, { only: 'prompts' });
                if (successMessage)
                    this.notifySuccess(successMessage);
                return data;
            })
            .catch((err) => {
                this.notifySaveError(err);
                throw err;
            })
            .finally(() => {
                this.savingPrompts = false;
            });
        },

        fieldMappingPayload: function(mapping, overrides = {}) {
            // Fields still on the default prompt are persisted with an empty prompt so
            // they keep following the default if it changes in a future version.
            return {
                entityType: mapping.entityType,
                fieldKey: mapping.fieldKey,
                enabled: mapping.enabled !== false,
                prompt: mapping.usingDefaultPrompt ? '' : String(mapping.prompt || ''),
                ...overrides
            };
        },

        toggleFieldEnabled: function(mapping, enabled) {
            if (!this.canEditPrompts || this.savingPrompts)
                return;

            const previous = mapping.enabled;
            mapping.enabled = enabled;
            this.startPromptToggleSaveStatus(`field:${toMappingKey(mapping)}`);

            return this.updatePrompts({
                promptMappings: [this.fieldMappingPayload(mapping, { enabled: enabled })]
            })
            .then(() => {
                // Only mirror the toggle; a full sync would discard unsaved prompt
                // edits when the panel is open on the same row.
                if (this.isEditorRow(mapping))
                    this.editor.enabled = enabled;
                this.finishPromptToggleSaveStatus();
            })
            .catch(() => {
                mapping.enabled = previous;
                this.clearPromptToggleSaveStatus();
            });
        },

        toggleGenericEnabled: function(entry, enabled) {
            if (!this.canEditPrompts || this.savingPrompts)
                return;

            this.startPromptToggleSaveStatus(`generic:${entry.id}`);
            const next = this.globalPrompts.map((item) => {
                return item.id === entry.id ? { ...item, enabled: enabled } : item;
            });

            return this.updatePrompts({
                globalPrompts: serializeGlobalPrompts(next)
            })
            .then(() => {
                if (this.editor?.kind === 'generic' && !this.editor.isNew && this.editor.id === entry.id)
                    this.editor.enabled = enabled;
                this.finishPromptToggleSaveStatus();
            })
            .catch(() => {
                this.clearPromptToggleSaveStatus();
            });
        },

        persistGenericOrder: function(list) {
            if (!this.canEditPrompts || this.savingPrompts || this.tableFilter.trim())
                return;

            const previous = this.globalPrompts;
            this.globalPrompts = list;

            this.updatePrompts({
                globalPrompts: serializeGlobalPrompts(list)
            }, null, { skipApply: true })
            .catch(() => {
                this.globalPrompts = previous;
            });
        },

        deleteSelectedGenericPrompts: function() {
            if (!this.canEditPrompts || this.selectedGenericIds.length === 0)
                return;

            const count = this.selectedGenericIds.length;
            this.confirmAction(
                this.$t('aiIntegration.prompts.deleteConfirmTitle'),
                this.$t('aiIntegration.prompts.deleteConfirmMessage', { count: count }),
                () => {
                    const removedIds = new Set(this.selectedGenericIds);
                    const next = this.globalPrompts.filter((entry) => !removedIds.has(entry.id));

                    this.updatePrompts({
                        globalPrompts: serializeGlobalPrompts(next)
                    }, this.$t('aiIntegration.prompts.deleteSuccess', { count: count }))
                    .then(() => {
                        if (this.editor?.kind === 'generic' && !this.editor.isNew && removedIds.has(this.editor.id))
                            this.editor = null;
                    })
                    .catch(() => {});
                }
            );
        },

        // Shared shape for every "confirm this negative/destructive action" dialog
        // in this page (delete, reset, discard unsaved changes).
        confirmAction: function(title, message, callback) {
            Dialog.create({
                title: title,
                message: message,
                ok: { label: this.$t('btn.confirm'), color: 'negative' },
                cancel: { label: this.$t('btn.cancel'), color: 'white' },
                focus: 'cancel'
            })
            .onOk(callback);
        },

        /* ===== Editor panel ===== */

        confirmDiscardEditor: function(callback) {
            if (!this.editorDirty) {
                callback();
                return;
            }

            this.confirmAction(
                this.$t('aiIntegration.prompts.discardChangesTitle'),
                this.$t('aiIntegration.prompts.discardChangesMessage'),
                callback
            );
        },

        // The tree uses a one-way :selected + @update:selected pair (rather than
        // v-model:selected) specifically so a dirty editor can be confirmed before
        // selectedNode changes, instead of changing it and reverting on cancel.
        selectTreeNode: function(key) {
            if (key === this.selectedNode)
                return;

            this.confirmDiscardEditor(() => {
                this.editor = null;
                this.selectedNode = key;
            });
        },

        openFieldEditor: function(mapping) {
            const mappingKey = toMappingKey(mapping);
            if (this.editor?.kind === 'field' && this.editor.mappingKey === mappingKey)
                return;

            this.confirmDiscardEditor(() => {
                this.editor = {
                    kind: 'field',
                    mappingKey: mappingKey,
                    enabled: mapping.enabled !== false,
                    prompt: String(mapping.prompt || '')
                };
            });
        },

        openGenericEditor: function(entry) {
            if (this.editor?.kind === 'generic' && !this.editor.isNew && this.editor.id === entry.id)
                return;

            this.confirmDiscardEditor(() => {
                this.editor = {
                    kind: 'generic',
                    isNew: false,
                    id: entry.id,
                    label: String(entry.label || ''),
                    prompt: String(entry.prompt || ''),
                    enabled: entry.enabled !== false
                };
            });
        },

        openNewGenericEditor: function() {
            this.confirmDiscardEditor(() => {
                this.editor = {
                    kind: 'generic',
                    isNew: true,
                    id: createGlobalPromptId(),
                    label: '',
                    prompt: '',
                    enabled: true
                };
            });
        },

        closeEditor: function() {
            this.confirmDiscardEditor(() => {
                this.editor = null;
            });
        },

        isEditorRow: function(mapping) {
            return this.editor?.kind === 'field' && this.editor.mappingKey === toMappingKey(mapping);
        },

        // Refresh the editor working copy after the server returned fresh data.
        syncEditorFromSource: function() {
            if (!this.editor)
                return;

            if (this.editor.kind === 'field') {
                const source = this.editorSourceMapping;
                if (!source) {
                    this.editor = null;
                    return;
                }
                this.editor.enabled = source.enabled !== false;
                this.editor.prompt = String(source.prompt || '');
                return;
            }

            if (this.editor.isNew)
                return;

            const source = this.editorSourceGeneric;
            if (!source) {
                this.editor = null;
                return;
            }
            this.editor.label = String(source.label || '');
            this.editor.prompt = String(source.prompt || '');
            this.editor.enabled = source.enabled !== false;
        },

        saveEditor: function() {
            if (!this.editorCanSave || this.savingEditor)
                return;

            let request = null;

            if (this.editor.kind === 'field') {
                const source = this.editorSourceMapping;
                if (!source)
                    return;

                request = this.updatePrompts({
                    promptMappings: [{
                        entityType: source.entityType,
                        fieldKey: source.fieldKey,
                        enabled: this.editor.enabled,
                        prompt: this.editor.prompt
                    }]
                }, this.$t('aiIntegration.prompts.saveSuccess'));
            } else {
                const entry = {
                    id: this.editor.id,
                    label: this.editor.label.trim(),
                    prompt: this.editor.prompt.trim(),
                    enabled: this.editor.enabled
                };

                const next = this.editor.isNew ?
                    [...this.globalPrompts, entry] :
                    this.globalPrompts.map((item) => item.id === entry.id ? entry : item);

                request = this.updatePrompts({
                    globalPrompts: serializeGlobalPrompts(next)
                }, this.$t('aiIntegration.prompts.saveSuccess'));
            }

            this.savingEditor = true;
            request
            .then(() => {
                if (this.editor?.kind === 'generic')
                    this.editor.isNew = false;
                this.syncEditorFromSource();
            })
            .catch(() => {})
            .finally(() => {
                this.savingEditor = false;
            });
        },

        resetFieldPrompt: function() {
            const source = this.editorSourceMapping;
            if (!this.canEditPrompts || !source)
                return;

            this.confirmAction(
                this.$t('aiIntegration.prompts.resetConfirmTitle'),
                this.$t('aiIntegration.prompts.resetConfirmMessage', { field: this.fieldDisplayLabel(source) }),
                () => {
                    this.updatePrompts({
                        promptMappings: [{
                            entityType: source.entityType,
                            fieldKey: source.fieldKey,
                            enabled: this.editor?.kind === 'field' ? this.editor.enabled : source.enabled !== false,
                            prompt: ''
                        }]
                    }, this.$t('aiIntegration.prompts.resetSuccess'))
                    .then(() => {
                        this.syncEditorFromSource();
                    })
                    .catch(() => {});
                }
            );
        },

        deleteEditorGenericPrompt: function() {
            if (!this.canEditPrompts || this.editor?.kind !== 'generic' || this.editor.isNew)
                return;

            const id = this.editor.id;
            this.confirmAction(
                this.$t('aiIntegration.prompts.deleteConfirmTitle'),
                this.$t('aiIntegration.prompts.deleteConfirmMessage', { count: 1 }),
                () => {
                    const next = this.globalPrompts.filter((entry) => entry.id !== id);

                    this.updatePrompts({
                        globalPrompts: serializeGlobalPrompts(next)
                    }, this.$t('aiIntegration.prompts.deleteSuccess', { count: 1 }))
                    .then(() => {
                        this.editor = null;
                    })
                    .catch(() => {});
                }
            );
        },

        /* ===== Redaction guidelines ===== */

        saveRedactionGuidelines: function() {
            if (!this.canEditGuidelines || this.savingGuidelines)
                return;

            this.savingGuidelines = true;
            DataService.updateAiIntegration({
                redactionGuidelines: serializeMarkdownInstructions(this.redactionGuidelines)
            })
            .then((data) => {
                this.applyPayload(data.data.datas || {});
                Notify.create({
                    message: this.$t('aiIntegration.guidelines.saveSuccess'),
                    color: 'positive',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .catch((err) => {
                Notify.create({
                    message: err.response?.data?.datas || this.$t('aiIntegration.guidelines.saveFailed'),
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .finally(() => {
                this.savingGuidelines = false;
            });
        }
    }
};
