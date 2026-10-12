import { Dialog, Notify } from 'quasar';
import { Cvss3P1, Cvss4P0 } from 'ae-cvss-calculator'

import BasicEditor from 'components/editor/Editor.vue';
import Cvss3Calculator from 'components/cvss3calculator'
import Cvss4Calculator from 'components/cvss4calculator'
import TextareaArray from 'components/textarea-array'
import CustomFields from 'components/custom-fields'
import DraftRecoveryStatus from 'components/draft-recovery-status.vue'

import VulnerabilityService from '@/services/vulnerability'
import DataService from '@/services/data'
import AiService from '@/services/ai'
import AiFieldHelper from '@/services/ai-field-helper'
import { useAiGenerationStore } from '@/stores/ai-generation'
import { useQaRunsStore } from '@/stores/qa-runs'
import { useVulnQaStore } from '@/stores/vuln-qa'
import { useUserStore } from 'src/stores/user'
import Utils from '@/services/utils'
import { createDraftRecovery } from '@/composables/useDraftRecovery'
import DraftRecoveryService from '@/services/draft-recovery'
import VulnerabilityQaPanel from '@/components/vulnerability-qa-panel.vue'
import VulnerabilityQaAllPanel from '@/components/vulnerability-qa-all-panel.vue'
import VulnerabilityUpdatesModal from '@/components/vulnerability-updates-modal.vue'
import AiChatDrawer from '@/components/ai-chat-drawer.vue'
import { canAccessQa } from '@/services/qa-checks'

import { $t } from 'boot/i18n'

const userStore = useUserStore()
const SAVE_SUCCESS_TIMEOUT_MS = 2000

// Memoized CVSS parsing per row object — rows are replaced on each list reload so
// stale entries are garbage collected with them.
const cvssCacheByRow = new WeakMap()

export default {
    data: () => {
        return {
            userStore: userStore,
            // Vulnerabilities list
            vulnerabilities: [],
            // Loading state
            loading: true,
            // List pagination
            pagination: {
                page: 1,
                rowsPerPage: 25,
                sortBy: 'title'
            },
            sortDesc: false,
            rowsPerPageOptions: [
                {label:'25', value:25},
                {label:'50', value:50},
                {label:'100', value:100},
                {label:'All', value:0}
            ],
            // Vulnerabilities languages
            languages: [],
            locale: '',
            // Search filter
            search: {title: '', categories: [], types: [], cvssRange: 'all', creator: null, unsavedOnly: false},
            // Text filters for the option lists inside the filter popover
            categoryFilterSearch: '',
            typeFilterSearch: '',
            // Status filter (single-select): all | valid | new | updates
            statusFilter: 'all',
            // Errors messages
            errors: {title: ''},
            // Selected or New Vulnerability
            currentVulnerability: {
                cvssv3: '',
                cvssv4: '',
                priority: '',
                remediationComplexity: '',
                details: []
            },
            currentVulnerabilityOrig: null,
            currentLanguage: "",
            dtLanguage: "",
            currentDetailsIndex: 0,
            vulnerabilityId: '',
            vulnUpdates: [],
            updatesModalOpen: false,
            vulnTypes: [],
            // Merge languages
            mergeLanguageLeft: '',
            mergeLanguageRight: '',
            mergeSearchLeft: '',
            mergeSearchRight: '',
            mergeVulnLeft: '',
            mergeVulnRight: '',
            // Vulnerability categories
            vulnCategories: [],
            currentCategory: null,
            // Custom Fields
            customFields: [],
            draftRecovery: null,
            draftRecoveryPaused: false,
            vulnerabilityDrafts: [],
            aiPromptFieldKeys: [],
            aiFieldPrompts: [],
            // Content displayed in the detail pane: null | create | edit | merge
            activePane: null,
            vulnQaOpen: false,
            saveSuccess: false,
            saveSuccessTimer: null,
            // Bumped after a save so the open QA panel(s) re-fetch their outdated state.
            qaReloadToken: 0,
            // Guards the route watcher from re-running while it drives a navigation itself.
            routeSyncing: false
        }
    },

    components: {
        BasicEditor,
        Cvss3Calculator,
        Cvss4Calculator,
        TextareaArray,
        CustomFields,
        DraftRecoveryStatus,
        AiChatDrawer,
        VulnerabilityQaPanel,
        VulnerabilityQaAllPanel,
        VulnerabilityUpdatesModal
    },

    mounted: function() {
        // Languages must be loaded before opening a vuln (clone() derives currentLanguage from
        // dtLanguage), so drive the initial route-based open off getLanguages resolving. The
        // detail fetch is independent of the (heavier) list load.
        this.getLanguages().then(() => {
            if (this.$route.params.vulnerabilityId)
                this.syncPaneWithRoute(this.$route.params.vulnerabilityId)
        })
        this.getVulnTypes()
        this.getVulnerabilities()
        this.getVulnerabilityCategories()
        this.getCustomFields()
        this.setupDraftRecovery()
        this.refreshVulnerabilityDrafts()
        this.loadAiEnabledFieldKeys()
        this.setupVulnQaSocket()
        document.addEventListener('keydown', this._listener, false)
    },

    unmounted: function() {
        document.removeEventListener('keydown', this._listener, false)
        if (this.draftRecovery)
            this.draftRecovery.stop()
        this.teardownVulnQaSocket()
        this.clearSaveSuccess()
    },

    watch: {
        // URL is the source of truth for which vulnerability is open: /vulnerabilities/<id>
        // opens its detail pane, /vulnerabilities (no id) closes it. Drives back/forward.
        '$route.params.vulnerabilityId': function(newId) {
            if (this.routeSyncing)
                return
            this.syncPaneWithRoute(newId)
        },
        currentLanguage: function(val, oldVal) {
            this.setCurrentDetails();
        },
        // The QA-all panel is per-locale: switching the list language re-attaches it (and
        // any in-flight job/state) to the newly selected locale.
        dtLanguage: function(val) {
            const vulnQaStore = useVulnQaStore()
            if (vulnQaStore.panelOpen && vulnQaStore.locale !== val)
                vulnQaStore.open(val)
        },
        draftRecoveryRevision: function() {
            this.refreshVulnerabilityDrafts()
        },
        filteredRowsCount: function() {
            // Keep the current page within bounds when filters shrink the list
            if (this.pagination.page > this.pagesNumber)
                this.pagination.page = Math.max(1, this.pagesNumber)
        },
        'pagination.rowsPerPage': function() {
            this.pagination.page = 1
        },
        currentVulnerability: {
            handler() {
                if (this.saveSuccess && this.hasUnsavedChanges)
                    this.clearSaveSuccess()
            },
            deep: true
        }
    },

    computed: {
        vulnTypesLang: function() {
            return this.vulnTypes.filter(type => type.locale === this.currentLanguage);
        },

        computedVulnerabilities: function() {
            var result = [];
            this.vulnerabilities.forEach(vuln => {
                for (var i=0; i<vuln.details.length; i++) {
                    if (vuln.details[i].locale === this.dtLanguage && vuln.details[i].title) {
                        result.push(vuln);
                    }
                }
            })
            return result;
        },

        statusCounts: function() {
            var counts = {all: this.computedVulnerabilities.length, valid: 0, new: 0, updates: 0}
            this.computedVulnerabilities.forEach(vuln => {
                if (vuln.status === 1)
                    counts.new += 1
                else if (vuln.status === 2)
                    counts.updates += 1
                else
                    counts.valid += 1
            })
            return counts
        },

        filteredVulnerabilities: function() {
            return this.customFilter(this.computedVulnerabilities, {...this.search, status: this.statusFilter})
        },

        filteredRowsCount: function() {
            return this.filteredVulnerabilities.length
        },

        sortedVulnerabilities: function() {
            return this.customSort(this.filteredVulnerabilities, this.pagination.sortBy, this.sortDesc)
        },

        pagesNumber: function() {
            if (!this.pagination.rowsPerPage)
                return 1
            return Math.max(1, Math.ceil(this.filteredRowsCount / this.pagination.rowsPerPage))
        },

        paginatedVulnerabilities: function() {
            if (!this.pagination.rowsPerPage)
                return this.sortedVulnerabilities
            var start = (this.pagination.page - 1) * this.pagination.rowsPerPage
            return this.sortedVulnerabilities.slice(start, start + this.pagination.rowsPerPage)
        },

        paginationRangeLabel: function() {
            if (this.filteredRowsCount === 0)
                return '0 - 0'
            if (!this.pagination.rowsPerPage)
                return `1 - ${this.filteredRowsCount}`
            var start = (this.pagination.page - 1) * this.pagination.rowsPerPage + 1
            var end = Math.min(this.filteredRowsCount, start + this.pagination.rowsPerPage - 1)
            return `${start} - ${end}`
        },

        activeFilterCount: function() {
            var count = 0
            if (this.search.categories.length > 0)
                count += 1
            if (this.search.types.length > 0)
                count += 1
            if (this.search.cvssRange !== 'all')
                count += 1
            if (this.search.creator)
                count += 1
            if (this.search.unsavedOnly)
                count += 1
            return count
        },

        unsavedChangesCount: function() {
            return this.computedVulnerabilities.filter(vuln =>
                this.hasDraftForVulnerability(vuln._id)
            ).length
        },

        categoryFacets: function() {
            var counts = {}
            this.computedVulnerabilities.forEach(vuln => {
                var name = vuln.category || 'No Category'
                counts[name] = (counts[name] || 0) + 1
            })
            var term = (this.categoryFilterSearch || '').toLowerCase()
            return this.vulnCategoriesOptions
                .filter(name => !term || name.toLowerCase().indexOf(term) > -1)
                .map(name => ({name: name, count: counts[name] || 0}))
        },

        typeFacets: function() {
            var counts = {}
            this.computedVulnerabilities.forEach(vuln => {
                var name = this.getDtType(vuln)
                counts[name] = (counts[name] || 0) + 1
            })
            var term = (this.typeFilterSearch || '').toLowerCase()
            return this.vulnTypeOptions
                .filter(name => !term || name.toLowerCase().indexOf(term) > -1)
                .map(name => ({name: name, count: counts[name] || 0}))
        },

        cvssFacets: function() {
            var counts = {all: this.computedVulnerabilities.length, low: 0, medium: 0, high: 0, critical: 0}
            this.computedVulnerabilities.forEach(vuln => {
                var bucket = this.getCvssBucket(vuln)
                if (bucket)
                    counts[bucket] += 1
            })
            return [
                {value: 'all', label: $t('all'), count: counts.all},
                {value: 'low', label: `0 – 3.9 (${$t('low')})`, count: counts.low},
                {value: 'medium', label: `4 – 6.9 (${$t('medium')})`, count: counts.medium},
                {value: 'high', label: `7 – 8.9 (${$t('high')})`, count: counts.high},
                {value: 'critical', label: `9 – 10 (${$t('critical')})`, count: counts.critical}
            ]
        },

        creatorOptions: function() {
            var names = new Set()
            this.vulnerabilities.forEach(vuln => {
                if (vuln.creator && vuln.creator.username)
                    names.add(vuln.creator.username)
            })
            return Array.from(names).sort((a, b) => a.localeCompare(b))
        },

        sortLabel: function() {
            var fieldLabels = {title: $t('title'), category: $t('category'), lastModified: $t('lastModified')}
            var direction
            if (this.pagination.sortBy === 'lastModified')
                direction = this.sortDesc ? $t('oldestFirst') : $t('newestFirst')
            else
                direction = this.sortDesc ? 'Z → A' : 'A → Z'
            return `${fieldLabels[this.pagination.sortBy] || this.pagination.sortBy} (${direction})`
        },

        vulnCategoriesOptions: function() {
            var result = this.vulnCategories.map(cat => {return cat.name})
            result.unshift('No Category')
            return result
        },

        vulnTypeOptions: function() {
            var result = this.vulnTypes.filter(type => type.locale === this.dtLanguage).map(type => {return type.name})
            result.unshift('Undefined')
            return result
        },

        filteredVulnerabilitiesMergeLeft: function() {
            const search = (this.mergeSearchLeft || '').trim().toLowerCase()
            return this.vulnerabilities.filter(vuln =>
                this.getVulnTitleLocale(vuln, this.mergeLanguageRight) === 'undefined' &&
                this.getVulnTitleLocale(vuln, this.mergeLanguageLeft) !== 'undefined' &&
                (!search || this.getVulnTitleLocale(vuln, this.mergeLanguageLeft).toLowerCase().includes(search))
            )
        },

        filteredVulnerabilitiesMergeRight: function() {
            const search = (this.mergeSearchRight || '').trim().toLowerCase()
            return this.vulnerabilities.filter(vuln =>
                this.getVulnTitleLocale(vuln, this.mergeLanguageLeft) === 'undefined' &&
                this.getVulnTitleLocale(vuln, this.mergeLanguageRight) !== 'undefined' &&
                (!search || this.getVulnTitleLocale(vuln, this.mergeLanguageRight).toLowerCase().includes(search))
            )
        },

        draftRecoveryRevision: function() {
            return DraftRecoveryService.state.revision
        },

        aiQaEnabled: function() {
            return canAccessQa(
                userStore.isAllowed('vulnerabilities:qa-read'),
                userStore.isAllowed('vulnerabilities:qa'),
                userStore.isAllowed('vulnerabilities:ai-qa'),
                this.$settings
            )
        },

        aiQaAllEnabled: function() {
            return canAccessQa(
                userStore.isAllowed('vulnerabilities:qa-read-catalog'),
                userStore.isAllowed('vulnerabilities:qa-catalog'),
                userStore.isAllowed('vulnerabilities:ai-qa-catalog'),
                this.$settings
            )
        },

        vulnerabilityQaCount: function() {
            return this.computedVulnerabilities.length
        },

        dtLanguageLabel: function() {
            return this.languages.find((entry) => entry.locale === this.dtLanguage)?.language || this.dtLanguage
        },

        aiEnabled: function() {
            return this.$settings?.ai?.public?.enabled !== false && (
                userStore.isAllowed('audits:ai-assist') ||
                userStore.isAllowed('vulnerabilities:ai-assist')
            )
        },

        aiDrawerOpen: function() {
            return useAiGenerationStore().drawerOpen
        },

        vulnQaAllOpen: function() {
            return useVulnQaStore().panelOpen
        },

        vulnQaAllRunning: function() {
            return useVulnQaStore().running
        },

        // The QA-all panel always renders as its own docked column (never inside a pane),
        // so navigating between vulnerabilities — which swaps the pane content — never
        // remounts it and the reviewer keeps their scroll position and expanded groups.
        vulnQaAllDockVisible: function() {
            return this.vulnQaAllOpen
        },

        // Run key for the QA panel of the vulnerability currently in the pane. Matches the
        // key computed inside vulnerability-qa-panel so the toolbar dot reflects its run even
        // when the panel is closed.
        activeVulnQaKey: function() {
            if (this.vulnerabilityId)
                return `vuln:${this.vulnerabilityId}:${this.currentLanguage}`
            return 'draft'
        },

        vulnQaRunning: function() {
            const qaRuns = useQaRunsStore()
            return qaRuns.isRunning(this.activeVulnQaKey) || qaRuns.isJobRunning(this.activeVulnQaKey)
        },

        // Whether the current pane's vulnerability content is editable: updating an existing
        // template needs vulnerabilities:update, creating a new one needs vulnerabilities:create.
        // A user without the right can still open the editor (read) but sees disabled fields.
        canEditVuln: function() {
            if (this.vulnerabilityId)
                return userStore.isAllowed('vulnerabilities:update')
            return userStore.isAllowed('vulnerabilities:create')
        },

        // The editor is read-only when the user can't edit this vulnerability.
        vulnReadonly: function() {
            return !this.canEditVuln
        },

        canUseAiInPane: function() {
            return this.aiEnabled && this.canEditVuln
        },

        hasUnsavedChanges: function() {
            return !!this.currentVulnerabilityOrig &&
                !this.$_.isEqual(this.currentVulnerability, this.currentVulnerabilityOrig)
        },

        saveButtonState: function() {
            if (this.hasUnsavedChanges)
                return 'dirty'
            return this.saveSuccess ? 'saved' : 'idle'
        },

        saveButtonColor: function() {
            if (this.saveButtonState === 'dirty')
                return 'orange'
            if (this.saveButtonState === 'saved')
                return 'green-1'
            return 'primary'
        },

        saveButtonTextColor: function() {
            if (this.saveButtonState === 'saved')
                return 'positive'
            if (this.saveButtonState === 'dirty')
                return 'orange'
            return 'primary'
        },

        saveButtonLabel: function() {
            if (this.saveButtonState === 'saved')
                return $t('btn.saved')
            return `${$t('btn.save')} (ctrl+s)`
        },

        currentCreatorName: function() {
            return this.currentVulnerability.creator?.username || ''
        }
    },

    methods: {
        // Get available languages
        getLanguages: function() {
            return DataService.getLanguages()
            .then((data) => {
                this.languages = data.data.datas;
                if (this.languages.length > 0) {
                    this.dtLanguage = this.languages[0].locale;
                    this.cleanCurrentVulnerability();
                }
            })
            .catch((err) => {
                console.log(err)
            })
        },

         // Get available custom fields
         getCustomFields: function() {
            DataService.getCustomFields()
            .then((data) => {
                this.customFields = data.data.datas
            })
            .catch((err) => {
                console.log(err)
            })
        },

        // Get Vulnerabilities types
        getVulnTypes: function() {
            DataService.getVulnerabilityTypes()
            .then((data) => {
                this.vulnTypes = data.data.datas;
            })
            .catch((err) => {
                console.log(err)
            })
        },

        // Get available vulnerability categories
        getVulnerabilityCategories: function() {
            DataService.getVulnerabilityCategories()
            .then((data) => {
                this.vulnCategories = data.data.datas;
            })
            .catch((err) => {
                console.log(err)
            })
        },

        getVulnerabilities: function() {
            this.loading = true
            return VulnerabilityService.getVulnerabilities()
            .then((data) => {
                this.vulnerabilities = data.data.datas
                this.loading = false
            })
            .catch((err) => {
                console.log(err)
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        createVulnerability: function() {
            Utils.syncEditors(this.$refs)
            this.cleanErrors();
            var index = this.currentVulnerability.details.findIndex(obj => obj.title !== '');
            if (index < 0)
                this.errors.title = $t('err.titleRequired');

            if (this.errors.title)
                return;

            const createdLocale = this.currentLanguage
            const createdTitle = this.currentVulnerability.details[index].title
            VulnerabilityService.createVulnerabilities([this.currentVulnerability])
            .then(async () => {
                if (this.draftRecovery)
                    this.draftRecovery.clearDraft()
                await this.getVulnerabilities()
                const created = this.vulnerabilities.find(vulnerability =>
                    vulnerability.details?.some(detail =>
                        detail.locale === createdLocale && detail.title === createdTitle
                    )
                )
                if (created) {
                    // The list now carries only lightweight rows, so keep the just-typed
                    // currentVulnerability (which holds the full content) and only adopt the
                    // new id/category rather than re-cloning the row.
                    this.vulnerabilityId = created._id
                    this.currentCategory = created.category ? {name: created.category} : null
                    this.currentVulnerability._id = created._id
                    this.currentVulnerability.status = 0
                    this.currentVulnerabilityOrig = this.$_.cloneDeep(this.currentVulnerability)
                    this.activePane = 'edit'
                    this.markSaveSuccess()
                    this.refreshQaAfterSave()
                    // Reflect the new vuln in the URL. The watcher no-ops (id already current).
                    if (this.$route.params.vulnerabilityId !== created._id) {
                        this.routeSyncing = true
                        this.$router.replace({ name: 'vulnerabilities', params: { vulnerabilityId: created._id } })
                            .catch(() => {})
                            .finally(() => { this.routeSyncing = false })
                    }
                }
            })
            .catch((err) => {
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        updateVulnerability: function() {
            Utils.syncEditors(this.$refs)
            this.cleanErrors();
            var index = this.currentVulnerability.details.findIndex(obj => obj.title !== '');
            if (index < 0)
                this.errors.title = $t('err.titleRequired');

            if (this.errors.title)
                return;

            // Only a content change can make the stored QA report outdated. A no-op save must
            // not flip the panel to "Run again", so refresh QA only when there were edits.
            const hadChanges = this.hasUnsavedChanges

            VulnerabilityService.updateVulnerability(this.vulnerabilityId, this.currentVulnerability)
            .then(() => {
                if (this.draftRecovery)
                    this.draftRecovery.clearDraft()
                this.currentVulnerability.status = 0
                this.currentVulnerabilityOrig = this.$_.cloneDeep(this.currentVulnerability)
                this.markSaveSuccess()
                if (hadChanges)
                    this.refreshQaAfterSave()
                this.getVulnerabilities()
            })
            .catch((err) => {
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        deleteVulnerability: function(vulnerabilityId) {
            VulnerabilityService.deleteVulnerability(vulnerabilityId)
            .then(() => {
                if (this.vulnerabilityId === vulnerabilityId)
                    this.closePane()
                this.getVulnerabilities();
                Notify.create({
                    message: $t('msg.vulnerabilityDeletedOk'),
                    color: 'positive',
                    textColor:'white',
                    position: 'top-right'
                })
            })
            .catch((err) => {
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        confirmDeleteVulnerability: function(row) {
            // Delete by the authoritative open-vuln id: the lazy-load create flow keeps the
            // typed object (which has no _id) as currentVulnerability, so fall back to
            // vulnerabilityId rather than trusting row._id.
            const vulnerabilityId = (row && row._id) || this.vulnerabilityId
            Dialog.create({
                title: $t('msg.confirmSuppression'),
                message: $t('msg.vulnerabilityWillBeDeleted'),
                ok: {label: $t('btn.confirm'), color: 'negative'},
                cancel: {label: $t('btn.cancel'), color: 'white'}
            })
            .onOk(() => this.deleteVulnerability(vulnerabilityId))
        },

        _listener: function(e) {
            if (!(window.navigator.platform.match('Mac') ? e.metaKey : e.ctrlKey) || e.keyCode !== 83)
                return

            e.preventDefault()
            if (this.activePane === 'create' && userStore.isAllowed('vulnerabilities:create'))
                this.createVulnerability()
            else if (this.activePane === 'edit' && userStore.isAllowed('vulnerabilities:update'))
                this.updateVulnerability()
        },

        markSaveSuccess: function() {
            this.clearSaveSuccess()
            this.saveSuccess = true
            this.saveSuccessTimer = setTimeout(() => {
                this.saveSuccess = false
                this.saveSuccessTimer = null
            }, SAVE_SUCCESS_TIMEOUT_MS)
        },

        clearSaveSuccess: function() {
            if (this.saveSuccessTimer) {
                clearTimeout(this.saveSuccessTimer)
                this.saveSuccessTimer = null
            }
            this.saveSuccess = false
        },

        // Called only after a content-changing save. Refresh the "outdated" signal that drives
        // the per-vuln "Run again" button and the QA-all panel — WITHOUT reloading the visible
        // report. Bumping qaReloadToken makes the open per-vuln panel re-fetch its report in
        // place (the stored issues are unchanged, so only the outdated flag / button flips; no
        // spinner, no flash). Other locales' cached reports are dropped so they re-fetch when
        // next opened, but the currently displayed one is never reset.
        refreshQaAfterSave: function() {
            this.qaReloadToken += 1
            if (this.vulnerabilityId) {
                const qaRuns = useQaRunsStore()
                this.languages
                    .filter((entry) => entry.locale !== this.currentLanguage)
                    .forEach((entry) => qaRuns.reset(`vuln:${this.vulnerabilityId}:${entry.locale}`))
            }
            const vulnQaStore = useVulnQaStore()
            if (vulnQaStore.panelOpen)
                vulnQaStore.loadStatus()
        },

        // Fetching proposals must never touch currentLanguage: the editor's selected language is
        // the user's, and each proposal is diffed against its own locale inside the modal.
        getVulnUpdates: function(vulnId) {
            return VulnerabilityService.getVulnUpdates(vulnId)
            .then((data) => {
                this.vulnUpdates = data.data.datas;
                this.vulnUpdates.forEach(vuln => {
                    vuln.customFields = Utils.filterCustomFields('vulnerability', this.currentVulnerability.category, this.customFields, vuln.customFields, vuln.locale)
                })
            })
            .catch((err) => {
                console.log(err)
            })
        },

        dismissUpdates: function(locale) {
            this.afterDismiss(VulnerabilityService.dismissVulnUpdates(this.vulnerabilityId, locale))
        },

        dismissUpdate: function(updateId) {
            this.afterDismiss(VulnerabilityService.dismissVulnUpdate(updateId))
        },

        dismissAllUpdates: function() {
            this.afterDismiss(VulnerabilityService.dismissAllVulnUpdates(this.vulnerabilityId))
        },

        afterDismiss: function(request) {
            request
            .then(() => {
                Notify.create({
                    message: $t('msg.updatesDismissedOk'),
                    color: 'positive',
                    textColor: 'white',
                    position: 'top-right'
                })
                return this.getVulnUpdates(this.vulnerabilityId)
            })
            .then(() => {
                if (this.vulnUpdates.length === 0) {
                    this.updatesModalOpen = false
                    this.currentVulnerability.status = 0
                }
                this.getVulnerabilities()
            })
            .catch((err) => {
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        clone: function(row) {
            this.cleanCurrentVulnerability();

            this.currentVulnerability = this.$_.cloneDeep(row)
            this.setCurrentDetails();
            this.currentVulnerabilityOrig = this.$_.cloneDeep(this.currentVulnerability)
            this.clearSaveSuccess()

            this.vulnerabilityId = row._id;
            if (userStore.isAllowed('vulnerabilities:update'))
                this.getVulnUpdates(this.vulnerabilityId);
        },

        // Selection goes through the router; the $route watcher performs the actual open so
        // the URL and browser history stay in sync with the visible pane.
        selectVulnerability: function(row) {
            if (this.$route.params.vulnerabilityId === row._id)
                return Promise.resolve()
            return this.$router.push({ name: 'vulnerabilities', params: { vulnerabilityId: row._id } }).catch(() => {})
        },

        // Reconcile the open pane with the URL. Present id -> fetch + open that vuln; absent id
        // -> close an open vuln pane (leaves the transient create/merge panes alone).
        syncPaneWithRoute: async function(routeId) {
            const id = routeId || this.$route.params.vulnerabilityId || null
            if (id) {
                if (id !== this.vulnerabilityId)
                    await this.openVulnerabilityById(id)
            } else if (this.activePane === 'edit') {
                await this.closePane({ skipRoutePush: true })
            }
        },

        // Full detail is fetched on demand (the list carries only lightweight rows).
        openVulnerabilityById: async function(vulnerabilityId) {
            try {
                const data = await VulnerabilityService.getVulnerability(vulnerabilityId)
                const vuln = data.data?.datas
                if (!vuln)
                    throw new Error('Vulnerability not found')
                await this.openVulnerability(vuln)
            } catch (err) {
                Notify.create({
                    message: err.response?.data?.datas || $t('vulnerabilityQa.notFoundInList'),
                    color: 'warning',
                    textColor: 'white',
                    position: 'top-right'
                })
                if (this.$route.params.vulnerabilityId === vulnerabilityId)
                    this.$router.push({ name: 'vulnerabilities' }).catch(() => {})
            }
        },

        openVulnerability: async function(row) {
            if (this.activePane)
                await this.cleanupCurrentVulnerability()

            this.clone(row)
            this.activePane = 'edit'
            this.scrollDetailToTop()
            await this.draftRecovery.maybePromptRecovery()
        },

        // Switching vulnerabilities swaps the pane content in place, which keeps the
        // previous scroll offset and lands the reader mid-form. Always reset to the top.
        // `detailScroll` is the active pane's scroll container (only one pane is mounted).
        scrollDetailToTop: function() {
            this.$nextTick(() => {
                if (typeof this.$refs.detailScroll?.scrollTo === 'function')
                    this.$refs.detailScroll.scrollTo({ top: 0 })
            })
        },

        openCreateVulnerability: async function(category) {
            // Create is a base-URL pane; drop any open vuln's id from the URL first (the route
            // watcher is suppressed so this method keeps ownership of the cleanup).
            await this.clearRouteVulnerability()
            if (this.activePane)
                await this.cleanupCurrentVulnerability()

            this.currentCategory = category ? this.$_.cloneDeep(category) : null
            this.vulnerabilityId = ''
            this.cleanCurrentVulnerability()
            this.currentVulnerabilityOrig = this.$_.cloneDeep(this.currentVulnerability)
            this.clearSaveSuccess()
            this.activePane = 'create'
            await this.draftRecovery.maybePromptRecovery()
        },

        openMergeVulnerabilities: async function() {
            if (this.activePane === 'merge')
                return
            await this.clearRouteVulnerability()
            if (this.activePane)
                await this.cleanupCurrentVulnerability()
            this.activePane = 'merge'
        },

        // Drop the open vuln's id from the URL without letting the route watcher also react
        // (the caller owns the pane transition that follows).
        clearRouteVulnerability: async function() {
            if (!this.$route.params.vulnerabilityId)
                return
            this.routeSyncing = true
            await this.$router.push({ name: 'vulnerabilities' }).catch(() => {})
            this.routeSyncing = false
        },

        closePane: async function(options = {}) {
            if (!this.activePane) {
                if (!options.skipRoutePush)
                    this.$router.push({ name: 'vulnerabilities' }).catch(() => {})
                return
            }
            if (this.activePane === 'merge') {
                this.activePane = null
                return
            }
            await this.cleanupCurrentVulnerability()
            this.activePane = null
            if (!options.skipRoutePush && this.$route.params.vulnerabilityId)
                this.$router.push({ name: 'vulnerabilities' }).catch(() => {})
        },

        cleanupCurrentVulnerability: async function() {
            const aiStore = useAiGenerationStore()
            if (aiStore.isActive)
                aiStore.cancelSession({ force: true })
            // The QA panel toggle is sticky across vuln navigation (like the audit QA panel):
            // it stays open so the next vuln's report shows without re-toggling. The panel is
            // keyed by vuln+locale, so it remounts and re-fetches for the newly opened vuln.
            // The unsaved-vulnerability QA run is tied to this pane session; drop it so the
            // next pane starts clean instead of showing a previous draft's results.
            useQaRunsStore().reset('draft')

            if (this.draftRecovery) {
                await this.draftRecovery.flushPendingWrite()
                this.draftRecovery.resetForKey()
            }
            this.draftRecoveryPaused = true
            this.vulnerabilityId = ''
            this.vulnUpdates = []
            this.updatesModalOpen = false
            this.currentCategory = null
            this.cleanCurrentVulnerability()
            this.currentVulnerabilityOrig = this.$_.cloneDeep(this.currentVulnerability)
            this.clearSaveSuccess()
            await this.$nextTick()
            this.draftRecoveryPaused = false
            await this.refreshVulnerabilityDrafts()
        },

        editChangeCategory: function(category) {
            Dialog.create({
                title: $t('msg.confirmCategoryChange'),
                message: $t('msg.categoryChangingNotice'),
                ok: {label: $t('btn.confirm'), color: 'negative'},
                cancel: {label: $t('btn.cancel'), color: 'white'}
            })
            .onOk(() => {
                if (category){
                    this.currentVulnerability.category = category.name
                }
                else {
                    this.currentVulnerability.category = null
                }
                if (!this.vulnerabilityId)
                    this.currentCategory = category ? this.$_.cloneDeep(category) : null
                this.setCurrentDetails()
            })
        },

        cleanErrors: function() {
            this.errors.title = '';
        },

        cleanCurrentVulnerability: function() {
            this.cleanErrors();
            this.currentVulnerability.cvssv3 = '';
            this.currentVulnerability.cvssv4 = '';
            this.currentVulnerability.priority = '';
            this.currentVulnerability.remediationComplexity = '';
            this.currentVulnerability.details = [];
            delete this.currentVulnerability.creator;
            this.currentLanguage = this.dtLanguage;
            if (this.currentCategory && this.currentCategory.name)
                this.currentVulnerability.category = this.currentCategory.name
            else
                this.currentVulnerability.category = null

            this.setCurrentDetails();
        },

        setupDraftRecovery: function() {
            if (this.draftRecovery)
                return

            this.draftRecovery = createDraftRecovery(this, {
                scope: () => this.vulnerabilityId ? 'vuln-modal-edit' : 'vuln-modal-create',
                refKey: () => this.vulnerabilityId || `_new:${this.currentCategory?.name || 'none'}`,
                userId: () => userStore.id,
                getCurrent: () => this.currentVulnerability,
                setCurrent: (data) => {
                    this.currentVulnerability = data
                    if (!this.vulnerabilityId && data.category)
                        this.currentCategory = { name: data.category }
                    this.setCurrentDetails()
                },
                getOriginal: () => this.currentVulnerabilityOrig,
                isDirty: () => !!this.currentVulnerabilityOrig && !this.$_.isEqual(this.currentVulnerability, this.currentVulnerabilityOrig),
                isReadOnly: () => this.draftRecoveryPaused || (this.vulnerabilityId ? !userStore.isAllowed('vulnerabilities:update') : !userStore.isAllowed('vulnerabilities:create')),
                afterRestore: async () => {
                    await this.$nextTick()
                }
            })
        },

        refreshVulnerabilityDrafts: async function() {
            if (!userStore.id) {
                this.vulnerabilityDrafts = []
                return
            }

            this.vulnerabilityDrafts = await DraftRecoveryService.listDrafts({
                userId: userStore.id,
                scopes: ['vuln-modal-edit', 'vuln-modal-create']
            })
        },

        hasDraftForVulnerability: function(vulnerabilityId) {
            if (!vulnerabilityId || this.vulnerabilityId === vulnerabilityId)
                return false
            return this.vulnerabilityDrafts.some(draft =>
                draft.scope === 'vuln-modal-edit' &&
                draft.refKey === vulnerabilityId
            )
        },

        hasCreateDraftForCategory: function(categoryName) {
            const refKey = `_new:${categoryName || 'none'}`
            return this.vulnerabilityDrafts.some(draft =>
                draft.scope === 'vuln-modal-create' &&
                draft.refKey === refKey
            )
        },

        // Create detail if locale doesn't exist else set the currentDetailIndex
        setCurrentDetails: function(value) {
            var index = this.currentVulnerability.details.findIndex(obj => obj.locale === this.currentLanguage);
            if (index < 0) {
                var details = {
                    locale: this.currentLanguage,
                    title: '',
                    vulnType: '',
                    description: '',
                    observation: '',
                    remediation: '',
                    references: [],
                    customFields: []
                }
                details.customFields = Utils.filterCustomFields('vulnerability', this.currentVulnerability.category, this.customFields, [], this.currentLanguage)

                this.currentVulnerability.details.push(details)
                index = this.currentVulnerability.details.length - 1;
            }
            else {
                this.currentVulnerability.details[index].customFields = Utils.filterCustomFields('vulnerability', this.currentVulnerability.category, this.customFields, this.currentVulnerability.details[index].customFields, this.currentLanguage)
            }
            this.currentDetailsIndex = index;
        },

        isTextInCustomFields: function(field) {

            if (this.currentVulnerability.details[this.currentDetailsIndex].customFields) {
                return typeof this.currentVulnerability.details[this.currentDetailsIndex].customFields.find(f => {
                    return f.customField === field.customField._id && f.text === field.text
                }) === 'undefined'
            }
            return false
        },

        getTextDiffInCustomFields: function(field) {
            var result = ''
            if (this.currentVulnerability.details[this.currentDetailsIndex].customFields) {
                this.currentVulnerability.details[this.currentDetailsIndex].customFields.find(f => {
                    if (f.customField === field.customField._id)
                        result = f.text
                })
            }
            return result
        },

        getDtTitle: function(row) {
            var index = row.details.findIndex(obj => obj.locale === this.dtLanguage);
            if (index < 0 || !row.details[index].title)
                return $t('err.notDefinedLanguage');
            else
                return row.details[index].title;
        },

        getDtType: function(row) {
            var index = row.details.findIndex(obj => obj.locale === this.dtLanguage);
            if (index < 0 || !row.details[index].vulnType)
                return "Undefined";
            else
                return row.details[index].vulnType;
        },

        getVulnCvss: function(row) {
            var scoring = this.$settings?.report?.public?.scoringMethods || {}
            var cacheKey = `${row.cvssv3 || ''}|${row.cvssv4 || ''}|${!!scoring.CVSS3}|${!!scoring.CVSS4}`
            var cached = cvssCacheByRow.get(row)
            if (cached && cached.key === cacheKey)
                return cached.value

            var cvss = null
            try {
                if (scoring.CVSS4 && row.cvssv4)
                    cvss = new Cvss4P0(row.cvssv4).createJsonSchema()
                else if (scoring.CVSS3 && row.cvssv3)
                    cvss = new Cvss3P1(row.cvssv3).createJsonSchema()
            } catch (err) {
                // Invalid CVSS format — ignore and treat as no CVSS
                cvss = null
            }

            var value = null
            if (cvss && typeof cvss.baseScore === 'number' && cvss.baseScore >= 0) {
                value = {
                    score: cvss.baseScore.toFixed(1),
                    scoreNum: cvss.baseScore,
                    color: this.getSeverityColor(cvss.baseSeverity)
                }
            }
            cvssCacheByRow.set(row, {key: cacheKey, value: value})
            return value
        },

        // Severity bucket used by the CVSS range filter; null when the row has no CVSS
        getCvssBucket: function(row) {
            var cvss = this.getVulnCvss(row)
            if (!cvss)
                return null
            if (cvss.scoreNum < 4)
                return 'low'
            if (cvss.scoreNum < 7)
                return 'medium'
            if (cvss.scoreNum < 9)
                return 'high'
            return 'critical'
        },

        getSeverityColor: function(severity) {
            var cvssColors = this.$settings?.report?.public?.cvssColors
            if (cvssColors) {
                var severityColorName = `${String(severity || 'None').toLowerCase()}Color`
                return cvssColors[severityColorName] || cvssColors.noneColor
            }
            switch (String(severity || '').toLowerCase()) {
                case 'low':
                    return 'green'
                case 'medium':
                    return 'orange'
                case 'high':
                    return 'red'
                case 'critical':
                    return 'black'
                default:
                    return 'blue'
            }
        },

        customSort: function(rows, sortBy, descending) {
            if (rows) {
                var data = [...rows];

                if (sortBy === 'lastModified') {
                    (descending)
                        ? data.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
                        : data.sort((a, b) => new Date(a.updatedAt) - new Date(b.updatedAt))
                }
                else if (sortBy === 'title') {
                    (descending)
                        ? data.sort((a, b) => this.getDtTitle(b).localeCompare(this.getDtTitle(a)))
                        : data.sort((a, b) => this.getDtTitle(a).localeCompare(this.getDtTitle(b)))
                }
                else if (sortBy === 'category') {
                    (descending)
                        ? data.sort((a, b) => (b.category || $t('noCategory')).localeCompare(a.category || $t('noCategory')))
                        : data.sort((a, b) => (a.category || $t('noCategory')).localeCompare(b.category || $t('noCategory')))
                }
                return data;
            }
        },

        setSort: function(sortBy) {
            if (this.pagination.sortBy === sortBy)
                this.sortDesc = !this.sortDesc
            else {
                this.pagination.sortBy = sortBy
                this.sortDesc = sortBy === 'lastModified'
            }
        },

        matchesStatusFilter: function(row, status) {
            if (status === 'valid')
                return row.status === 0
            if (status === 'new')
                return row.status === 1
            if (status === 'updates')
                return row.status === 2
            return true
        },

        customFilter: function(rows, terms) {
            var termTitle = (terms.title || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
            var categories = terms.categories || []
            var types = terms.types || []
            var cvssRange = terms.cvssRange || 'all'
            var result = rows && rows.filter(row => {
                var title = this.getDtTitle(row).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
                return title.indexOf(termTitle) > -1 &&
                (categories.length === 0 || categories.includes(row.category || 'No Category')) &&
                (types.length === 0 || types.includes(this.getDtType(row))) &&
                (cvssRange === 'all' || this.getCvssBucket(row) === cvssRange) &&
                (!terms.creator || row.creator?.username === terms.creator) &&
                (!terms.unsavedOnly || this.hasDraftForVulnerability(row._id)) &&
                this.matchesStatusFilter(row, terms.status || 'all')
            })
            return result || [];
        },

        resetAdvancedFilters: function() {
            this.search.categories = []
            this.search.types = []
            this.search.cvssRange = 'all'
            this.search.creator = null
            this.search.unsavedOnly = false
            this.categoryFilterSearch = ''
            this.typeFilterSearch = ''
        },

        goToAudits: function(row) {
            var title = this.getDtTitle(row);
            this.$router.push({name: 'audits', query: {findingTitle: title}});
        },

        // Exactly one right-hand panel is visible at a time: per-vuln QA ('qa'), the AI
        // chat drawer ('ai'), or the QA-all panel ('qa-all'). Opening one closes the others.
        prepareSidePanelForPane: function(except) {
            if (except !== 'qa')
                this.vulnQaOpen = false
            if (except !== 'ai') {
                const aiStore = useAiGenerationStore()
                if (aiStore.isActive)
                    aiStore.cancelSession({ force: true })
            }
            if (except !== 'qa-all')
                useVulnQaStore().close()
        },

        toggleVulnerabilityQaView: function() {
            if (this.vulnQaOpen) {
                this.vulnQaOpen = false
                return
            }

            Utils.syncEditors(this.$refs)
            this.prepareSidePanelForPane('qa')
            this.vulnQaOpen = true
        },

        closeVulnQa: function() {
            this.vulnQaOpen = false
        },

        toggleRunAllQa: function() {
            const vulnQaStore = useVulnQaStore()
            if (vulnQaStore.panelOpen) {
                vulnQaStore.close()
                return
            }
            if (!this.vulnerabilityQaCount)
                return

            this.prepareSidePanelForPane('qa-all')
            vulnQaStore.open(this.dtLanguage)
        },

        // Issue click in the QA-all panel: select the offending vulnerability in the list
        // (paging/scrolling to it) and open its edit pane — the panel follows into the
        // pane's side slot, so triage flow is click → fix → recheck → next.
        navigateToVulnerabilityFromQa: async function(vulnerabilityId) {
            const vuln = this.vulnerabilities.find((row) => row._id === vulnerabilityId)
            if (!vuln) {
                // Deleted since the QA run: without feedback the button looks broken.
                Notify.create({
                    message: $t('vulnerabilityQa.notFoundInList'),
                    color: 'warning',
                    textColor: 'white',
                    position: 'top-right'
                })
                return
            }

            const index = this.sortedVulnerabilities.findIndex((row) => row._id === vulnerabilityId)
            if (index === -1) {
                Notify.create({
                    message: $t('vulnerabilityQa.notVisibleWithFilters'),
                    color: 'info',
                    textColor: 'white',
                    position: 'top-right',
                    actions: [{
                        label: $t('vulnerabilityQa.clearFilters'),
                        color: 'white',
                        handler: () => {
                            this.clearListFilters()
                            this.navigateToVulnerabilityFromQa(vulnerabilityId)
                        }
                    }]
                })
            } else if (this.pagination.rowsPerPage) {
                this.pagination.page = Math.floor(index / this.pagination.rowsPerPage) + 1
            }

            await this.selectVulnerability(vuln)
            this.$nextTick(() => {
                const visibleIndex = this.pagination.rowsPerPage
                    ? index % this.pagination.rowsPerPage
                    : index
                if (this.$refs.vulnerabilityList?.scrollTo)
                    this.$refs.vulnerabilityList.scrollTo(visibleIndex, 'center-force')
                else
                    document.querySelector(`[data-testid="vulnerability-item-${vulnerabilityId}"]`)
                        ?.scrollIntoView({ block: 'nearest' })
            })
        },

        clearListFilters: function() {
            this.search = {title: '', categories: [], types: [], cvssRange: 'all', creator: null, unsavedOnly: false}
            this.statusFilter = 'all'
        },

        setupVulnQaSocket: function() {
            const vulnQaStore = useVulnQaStore()
            this.vulnQaSocketHandlers = {
                progress: (payload) => vulnQaStore.handleSocketProgress(payload),
                done: (payload) => vulnQaStore.handleSocketDone(payload),
                singleDone: (payload) => this.handleSingleVulnQaDone(payload),
                connect: () => this.$socket.emit('join', { username: userStore.username, room: 'vuln-qa' })
            }
            this.$socket.emit('join', { username: userStore.username, room: 'vuln-qa' })
            this.$socket.on('vuln-qa:progress', this.vulnQaSocketHandlers.progress)
            this.$socket.on('vuln-qa:done', this.vulnQaSocketHandlers.done)
            this.$socket.on('vuln-qa-single:done', this.vulnQaSocketHandlers.singleDone)
            this.$socket.on('connect', this.vulnQaSocketHandlers.connect)
        },

        teardownVulnQaSocket: function() {
            if (!this.vulnQaSocketHandlers)
                return
            // Remove only this page's listeners — the boot file's global connect/disconnect
            // handlers must survive, so never call a bare $socket.off().
            this.$socket.emit('leave', { username: userStore.username, room: 'vuln-qa' })
            this.$socket.off('vuln-qa:progress', this.vulnQaSocketHandlers.progress)
            this.$socket.off('vuln-qa:done', this.vulnQaSocketHandlers.done)
            this.$socket.off('vuln-qa-single:done', this.vulnQaSocketHandlers.singleDone)
            this.$socket.off('connect', this.vulnQaSocketHandlers.connect)
            this.vulnQaSocketHandlers = null
            useVulnQaStore().clearStatusRefresh()
        },

        // A single-vuln QA run is a server-side background job; on its :done event refetch
        // the persisted report into qa-runs.js, clear any recheck-row spinner, and refresh
        // the QA-all view if it's showing this locale.
        handleSingleVulnQaDone: function(payload) {
            if (!payload?.vulnerabilityId || !payload?.locale)
                return

            const qaRuns = useQaRunsStore()
            const key = `vuln:${payload.vulnerabilityId}:${payload.locale}`
            qaRuns.setJob(key, payload)
            qaRuns.load(
                key,
                () => AiService.runVulnerabilityQa({
                    vulnerabilityId: payload.vulnerabilityId,
                    locale: payload.locale,
                    loadOnly: true
                }).then((response) => {
                    const datas = response.data.datas || {}
                    qaRuns.setJob(key, datas.job || null)
                    return datas
                }),
                { errorFallback: $t('vulnerabilityQa.failed') }
            )

            const vulnQaStore = useVulnQaStore()
            vulnQaStore.finishRecheck(payload.vulnerabilityId)
            if (vulnQaStore.locale === payload.locale)
                vulnQaStore.loadStatus()
        },

        getVulnTitleLocale: function(vuln, locale) {
            for (var i=0; i<vuln.details.length; i++) {
                if (vuln.details[i].locale === locale && vuln.details[i].title) return vuln.details[i].title;
            }
            return "undefined";
        },

        mergeVulnerabilities: function() {
            VulnerabilityService.mergeVulnerability(this.mergeVulnLeft, this.mergeVulnRight, this.mergeLanguageRight)
            .then(() => {
                this.mergeVulnLeft = ''
                this.mergeVulnRight = ''
                this.getVulnerabilities();
                Notify.create({
                    message: $t('msg.vulnerabilityMergeOk'),
                    color: 'positive',
                    textColor:'white',
                    position: 'top-right'
                })
            })
            .catch((err) => {
                Notify.create({
                    message: err.response.data.datas,
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            })
        },

        loadAiEnabledFieldKeys: function() {
            if (!this.aiEnabled) {
                this.aiPromptFieldKeys = []
                this.aiFieldPrompts = []
                return
            }

            AiService.getEnabledFields('finding')
            .then((data) => {
                const fields = data.data.datas?.fields || []
                this.aiFieldPrompts = fields
                this.aiPromptFieldKeys = fields
                    .map((field) => String(field.fieldKey || ''))
                    .filter((fieldKey) => fieldKey !== 'poc')
            })
            .catch(() => {
                this.aiPromptFieldKeys = []
                this.aiFieldPrompts = []
            })
        },

        getCustomFieldAiKey: function(customFieldId) {
            return `custom-field:${customFieldId}`
        },

        canGenerateAi: function(fieldKey) {
            return this.canUseAiInPane && this.aiPromptFieldKeys.includes(fieldKey)
        },

        buildAiLockKey: function(fieldKey) {
            const vulnKey = this.vulnerabilityId || `new:${this.currentCategory?.name || 'none'}`
            return `vulnerability:${vulnKey}:${this.currentLanguage}:${fieldKey}`
        },

        isAiFieldLoading: function(fieldKey) {
            return useAiGenerationStore().isFieldGenerating(this.buildAiLockKey(fieldKey))
        },

        isAiFieldSessionActive: function(fieldKey) {
            return AiFieldHelper.isFieldSessionActive(this.buildAiLockKey(fieldKey))
        },

        isAiFieldSelectionLocked: function(fieldKey) {
            return AiFieldHelper.isFieldSelectionLocked(this.buildAiLockKey(fieldKey))
        },

        isFieldEditable: function(fieldKey) {
            return this.canUseAiInPane
        },

        getCurrentDetail: function() {
            return this.currentVulnerability.details[this.currentDetailsIndex] || {}
        },

        getAiSelectionTarget: function(field, customField = null) {
            if (customField)
                return this.$refs.customfields?.getAiSelectionTarget?.(customField) || null

            if (field === 'references')
                return this.$refs.referencesField || null

            return this.$refs[`basiceditor_${field}`] || null
        },

        generateCustomFieldDraftAI: function(customField) {
            return this.generateFieldDraftAI(null, customField)
        },

        generateFieldDraftAI: async function(field, customField = null) {
            const fieldKey = customField ? this.getCustomFieldAiKey(customField?.customField?._id) : field
            if (!fieldKey || !this.canGenerateAi(fieldKey))
                return

            if (!this.canUseAiInPane || this.isAiFieldLoading(fieldKey))
                return

            this.prepareSidePanelForPane('ai')

            const lockKey = this.buildAiLockKey(fieldKey)
            const aiStore = useAiGenerationStore()
            if (aiStore.drawerOpen && aiStore.isActive && aiStore.lockKey !== lockKey) {
                Notify.create({
                    message: $t('aiChat.activeSession'),
                    color: 'warning',
                    textColor: 'dark',
                    position: 'top-right'
                })
                return
            }

            Utils.syncEditors(this.$refs)

            const detail = this.getCurrentDetail()

            try {
                await AiFieldHelper.runFieldSession({
                    field,
                    customField,
                    fieldKey,
                    lockKey,
                    selectionTarget: this.getAiSelectionTarget(field, customField),
                    entityShape: 'vulnerability',
                    requestEntityType: 'finding',
                    locale: this.currentLanguage,
                    aiFieldPrompts: this.aiFieldPrompts,
                    languages: this.languages,
                    buildContext: () => AiFieldHelper.buildVulnerabilityAiContext(this.currentVulnerability, detail, customField),
                    getDiffEntity: () => {
                        Utils.syncEditors(this.$refs)
                        return this.currentVulnerability
                    },
                    setValue: (value) => {
                        if (customField)
                            customField.text = value
                        else
                            detail[field] = value
                    }
                })
            } catch (err) {
                Notify.create({
                    message: err.response?.data?.datas || err.message || 'Unable to generate AI draft',
                    color: 'negative',
                    textColor: 'white',
                    position: 'top-right'
                })
            }
        }
    }
}
