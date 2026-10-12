import { Notify, Dialog } from 'quasar';
import DataService from '@/services/data';
import { useUserStore } from '@/stores/user';
import { $t } from '@/boot/i18n';
import {
    QA_PROGRAMMATIC_CHECK_KEYS,
    QA_AI_CHECK_KEYS
} from '@/services/qa-checks';
import {
    defaultMarkdownInstructions,
    serializeMarkdownInstructions
} from '@/pages/data/ai-integration-shared';

const userStore = useUserStore();

const defaultQaChecks = () => ({
    completeness: true,
    references: true,
    imageCaptions: true,
    duplicates: true,
    aiDuplicates: true,
    aiUnlinkedTranslations: true,
    redaction: true,
    customer: true,
    instructions: true
});

const QA_CHECK_I18N_KEYS = {
    completeness: 'checkCompleteness',
    references: 'checkReferences',
    imageCaptions: 'checkImageCaptions',
    duplicates: 'checkDuplicates',
    aiDuplicates: 'checkAiDuplicates',
    aiUnlinkedTranslations: 'checkAiUnlinkedTranslations',
    redaction: 'checkRedaction',
    customer: 'checkCustomer',
    instructions: 'checkInstructions'
};

const QA_CHECK_ICONS = {
    completeness: 'fact_check',
    references: 'link',
    imageCaptions: 'image',
    duplicates: 'content_copy',
    aiDuplicates: 'auto_awesome',
    aiUnlinkedTranslations: 'language',
    redaction: 'edit_note',
    customer: 'business',
    instructions: 'checklist'
};

// Mirrors what the backend actually scopes each check to (backend/src/lib/ai-qa.js and
// ai-vuln-qa.js): only the duplicate-detection checks are vulnerability-database-only,
// everything else runs against both audit reports and vulnerability templates.
const QA_CHECK_SCOPES = {
    completeness: ['audit', 'vulnerability'],
    references: ['audit', 'vulnerability'],
    imageCaptions: ['audit', 'vulnerability'],
    duplicates: ['vulnerability'],
    aiDuplicates: ['vulnerability'],
    aiUnlinkedTranslations: ['vulnerability'],
    redaction: ['audit', 'vulnerability'],
    customer: ['audit', 'vulnerability'],
    instructions: ['audit', 'vulnerability']
};

const buildQaCheckOptions = (keys) => {
    return keys.map((key) => ({
        key: key,
        label: $t(`aiIntegration.qa.${QA_CHECK_I18N_KEYS[key]}Label`),
        description: $t(`aiIntegration.qa.${QA_CHECK_I18N_KEYS[key]}Description`),
        icon: QA_CHECK_ICONS[key],
        scopes: QA_CHECK_SCOPES[key] || []
    }));
};

const serializeQaChecks = (checks = {}) => ({
    completeness: checks.completeness !== false,
    references: checks.references !== false,
    imageCaptions: checks.imageCaptions !== false,
    duplicates: checks.duplicates !== false,
    aiDuplicates: checks.aiDuplicates !== false,
    aiUnlinkedTranslations: checks.aiUnlinkedTranslations !== false,
    redaction: checks.redaction !== false,
    customer: checks.customer !== false,
    instructions: checks.instructions !== false
});

export default {
    beforeRouteLeave(to, from, next) {
        if (this.hasQaChanges) {
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
            savingQaSettings: false,
            canEditQa: userStore.isAllowed('ai:qa-instructions:update'),
            canReadQa: userStore.isAllowed('ai:qa-instructions:read'),
            // Built-in checks run regardless of AI integration; only the AI checks depend
            // on it. aiEnabled drives the informational banner, not page visibility.
            aiEnabled: true,
            qaInstructions: defaultMarkdownInstructions(),
            qaChecks: defaultQaChecks(),
            qaInstructionsExpanded: false,
            qaToggleSaveKey: null,
            qaToggleSaveState: null,
            qaToggleSaveTimer: null,
            orig: {
                qaInstructions: serializeMarkdownInstructions(),
                qaChecks: serializeQaChecks()
            }
        };
    },

    mounted: function() {
        this.getAiIntegration();
    },

    beforeUnmount: function() {
        if (this.qaToggleSaveTimer)
            clearTimeout(this.qaToggleSaveTimer);
    },

    computed: {
        pageTitle: function() {
            return this.$t('aiIntegration.pageTitleQa');
        },

        canViewPage: function() {
            return this.canReadQa;
        },

        programmaticQaCheckOptions: function() {
            return buildQaCheckOptions(QA_PROGRAMMATIC_CHECK_KEYS);
        },

        aiQaCheckOptions: function() {
            return buildQaCheckOptions(QA_AI_CHECK_KEYS);
        },

        hasQaInstructionChanges: function() {
            return JSON.stringify(
                serializeMarkdownInstructions(this.qaInstructions)
            ) !== JSON.stringify(this.orig.qaInstructions);
        },

        hasQaCheckChanges: function() {
            return JSON.stringify(
                serializeQaChecks(this.qaChecks)
            ) !== JSON.stringify(this.orig.qaChecks);
        },

        hasQaChanges: function() {
            return this.hasQaInstructionChanges || this.hasQaCheckChanges;
        }
    },

    methods: {
        applyPayload: function(payload) {
            this.aiEnabled = payload.aiEnabled !== false;

            if (payload.qaInstructions) {
                const qaInstructions = payload.qaInstructions;
                this.qaInstructions = {
                    content: String(qaInstructions.content || '')
                };
                this.orig.qaInstructions = serializeMarkdownInstructions(this.qaInstructions);
            }

            if (payload.qaChecks) {
                this.qaChecks = serializeQaChecks(payload.qaChecks);
                this.orig.qaChecks = serializeQaChecks(this.qaChecks);
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
            });
        },

        scopeLabel: function(scope) {
            return scope === 'audit' ? this.$t('aiIntegration.qa.scopeAudit') : this.$t('aiIntegration.qa.scopeVulnerability');
        },

        refreshPublicSettings: async function() {
            if (this.$settings?.refresh)
                await this.$settings.refresh();
        },

        clearQaToggleSaveStatus: function() {
            if (this.qaToggleSaveTimer)
                clearTimeout(this.qaToggleSaveTimer);
            this.qaToggleSaveTimer = null;
            this.qaToggleSaveKey = null;
            this.qaToggleSaveState = null;
        },

        toggleQaCheck: function(key, enabled) {
            if (!this.canEditQa || this.savingQaSettings)
                return;

            const previous = this.qaChecks[key];
            this.qaChecks[key] = enabled;
            this.savingQaSettings = true;
            this.clearQaToggleSaveStatus();
            this.qaToggleSaveKey = key;
            this.qaToggleSaveState = 'saving';

            return DataService.updateAiIntegration({
                qaChecks: serializeQaChecks(this.qaChecks)
            })
            .then(async (data) => {
                const returnedChecks = data.data.datas?.qaChecks;
                this.qaChecks = returnedChecks ? serializeQaChecks(returnedChecks) : serializeQaChecks(this.qaChecks);
                this.orig.qaChecks = serializeQaChecks(this.qaChecks);
                await this.refreshPublicSettings();
                this.qaToggleSaveState = 'saved';
                this.qaToggleSaveTimer = setTimeout(() => {
                    this.clearQaToggleSaveStatus();
                }, 2000);
            })
            .catch((err) => {
                this.qaChecks[key] = previous;
                this.clearQaToggleSaveStatus();
                Notify.create({
                    message: err.response?.data?.datas || this.$t('aiIntegration.qa.saveFailed'),
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .finally(() => {
                this.savingQaSettings = false;
            });
        },

        saveQaSettings: function() {
            if (!this.canEditQa || this.savingQaSettings || !this.hasQaChanges)
                return;

            this.savingQaSettings = true;
            const payload = {};

            if (this.hasQaCheckChanges)
                payload.qaChecks = serializeQaChecks(this.qaChecks);

            if (this.hasQaInstructionChanges)
                payload.qaInstructions = serializeMarkdownInstructions(this.qaInstructions);

            DataService.updateAiIntegration(payload)
            .then(async (data) => {
                this.applyPayload(data.data.datas || {});
                await this.refreshPublicSettings();
                Notify.create({
                    message: this.$t('aiIntegration.qa.saveSuccess'),
                    color: 'positive',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .catch((err) => {
                Notify.create({
                    message: err.response?.data?.datas || this.$t('aiIntegration.qa.saveFailed'),
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                });
            })
            .finally(() => {
                this.savingQaSettings = false;
            });
        }
    }
};
