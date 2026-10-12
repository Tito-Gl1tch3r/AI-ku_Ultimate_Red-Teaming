(function() {
    function normalizePluginAiInput(promptOverride = '', input = '') {
        return sanitizePluginAiMessageInput(promptOverride || input);
    }

    function sanitizePluginAiMessageInput(text) {
        return String(text || '').trim();
    }

    function normalizePluginAiMessagesPayload(data = {}) {
        return Array.isArray(data.messages) ? data.messages : [];
    }

    function extractToolEventsFromMessages(messages = []) {
        return messages.flatMap((message) => {
            const events = [];
            const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : [];
            const toolResults = Array.isArray(message.tool_results) ? message.tool_results : [];
            toolCalls.forEach((item) => events.push({ type: 'tool_call', data: item }));
            toolResults.forEach((item) => events.push({ type: 'tool_result', data: item }));
            return events;
        });
    }

    function shortenPluginAiPath(value = '', options = {}) {
        const raw = String(value || '').trim();
        if (!raw) return '';
        const workspaceRoot = String(options.workspaceRoot || '').trim().replace(/\\/g, '/');
        const normalized = raw.replace(/\\/g, '/');
        let compact = normalized;

        if (workspaceRoot && normalized.startsWith(workspaceRoot)) {
            compact = normalized.slice(workspaceRoot.length).replace(/^\/+/, '');
        }

        compact = compact
            .replace(/^\/app\/(Plugins|Themes)\/[^/]+\/source\/?/i, '')
            .replace(/^\/Users\/[^/]+\/Desktop\/Temodar Agent\/(Plugins|Themes)\/[^/]+\/source\/?/i, '')
            .replace(/^\.\//, '');

        if (!compact) return '.';
        const segments = compact.split('/').filter(Boolean);
        if (segments.length <= 4) return compact;
        return `…/${segments.slice(-4).join('/')}`;
    }

    function truncatePluginAiText(value = '', maxLength = 110) {
        const text = String(value || '').replace(/\s+/g, ' ').trim();
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
    }

    function shortenPluginAiPattern(value = '') {
        return truncatePluginAiText(String(value || '').trim(), 44);
    }

    function groupPluginAiActivityEntries(entries = []) {
        const grouped = [];
        (Array.isArray(entries) ? entries : []).forEach((entry) => {
            if (!entry) return;
            const previous = grouped[grouped.length - 1];
            const canGroup = previous
                && previous.type === entry.type
                && previous.label === entry.label
                && previous.category === entry.category
                && previous.detail === entry.detail
                && previous.state === entry.state;

            if (canGroup) {
                previous.count = (previous.count || 1) + 1;
                previous.id = `${previous.id}-${previous.count}`;
                return;
            }

            grouped.push({ ...entry, count: entry.count || 1 });
        });
        return grouped;
    }

    function buildPluginAiActivityEntries(events = [], options = {}) {
        const liveOptions = options && typeof options === 'object' ? options : {};
        const showSource = !!liveOptions.showSource;
        const workspaceRoot = String(liveOptions.workspaceRoot || '').trim();
        const rawEntries = (Array.isArray(events) ? events : []).map((event, index) => {
            const type = String(event?.type || 'event');
            const data = event?.data && typeof event.data === 'object' ? event.data : {};
            const toolName = String(data.name || data.toolName || data.tool || '').trim();
            const input = data.input && typeof data.input === 'object' ? data.input : data;
            let label = 'Activity';
            let detail = '';
            let icon = '•';
            let tone = 'neutral';
            let category = 'activity';
            let state = 'done';
            let hidden = false;

            if (type === 'tool_call') {
                category = 'tool';
                tone = 'running';
                state = 'active';
                if (toolName === 'read' || toolName === 'file_read') {
                    label = 'File read';
                    detail = shortenPluginAiPath(String(input.path || data.path || '(no path)'), { workspaceRoot });
                    icon = '📄';
                } else if (toolName === 'grep') {
                    label = 'Code search';
                    const pattern = shortenPluginAiPattern(input.pattern || '');
                    const path = shortenPluginAiPath(String(input.path || ''), { workspaceRoot });
                    detail = [pattern ? `pattern: ${pattern}` : '', path ? `path: ${path}` : ''].filter(Boolean).join(' • ');
                    icon = '⌕';
                } else if (toolName === 'bash') {
                    label = 'Bash';
                    detail = truncatePluginAiText(String(input.command || data.command || '(no command)'), 96);
                    icon = '⌘';
                } else if (toolName === 'edit' || toolName === 'file_edit') {
                    label = 'File edited';
                    detail = shortenPluginAiPath(String(input.path || data.path || '(no path)'), { workspaceRoot });
                    icon = '✎';
                } else if (toolName === 'write' || toolName === 'file_write') {
                    label = 'File written';
                    detail = shortenPluginAiPath(String(input.path || data.path || '(no path)'), { workspaceRoot });
                    icon = '✚';
                } else if (toolName === 'run_semgrep') {
                    label = 'Semgrep';
                    detail = truncatePluginAiText(String(input.config || data.config || 'auto'), 72);
                    icon = 'S';
                } else {
                    label = 'Tool';
                    detail = truncatePluginAiText([toolName || 'tool', shortenPluginAiPath(String(input.path || input.command || data.path || data.command || '').trim(), { workspaceRoot })].filter(Boolean).join(' • '), 96);
                    icon = '⋯';
                }
            } else {
                hidden = true;
            }

            return {
                id: `${type}-${index}`,
                type,
                label,
                detail,
                icon,
                tone,
                category,
                state,
                hidden,
                toolName,
                toolTone: pluginAiToolBadgeTone(toolName),
                bashCommand: toolName === 'bash' ? String(input.command || data.command || '').trim() : '',
            };
        }).filter((entry) => !entry.hidden);

        const groupedEntries = groupPluginAiActivityEntries(rawEntries);
        const lastActiveIndex = [...groupedEntries].map((entry, index) => ({ entry, index })).reverse().find((item) => item.entry.state === 'active')?.index;
        return groupedEntries.map((entry, index) => ({
            ...entry,
            isCurrent: lastActiveIndex === index,
        }));
    }

    function describeAiActivityEvent(event = {}) {
        const entry = buildPluginAiActivityEntries([event])[0];
        return entry ? `${entry.label}${entry.detail ? `: ${entry.detail}` : ''}` : 'Activity';
    }

    function formatPluginAiActivity(event = {}) {
        const type = String(event?.type || '');
        const data = event?.data && typeof event.data === 'object' ? event.data : event;

        if (type === 'agent_started') {
            return `Agent started: ${String(data?.name || 'unknown')}`;
        }
        if (type === 'agent_completed') {
            return `Agent completed: ${String(data?.name || 'unknown')}`;
        }
        if (type === 'task_started') {
            return `Task started: ${String(data?.title || data?.id || 'task')}`;
        }
        if (type === 'task_completed') {
            return `Task completed: ${String(data?.title || data?.id || 'task')}`;
        }
        if (type === 'task_failed') {
            return `Task failed: ${String(data?.title || data?.id || 'task')}`;
        }
        if (type === 'team_started') {
            return `Team started: ${String(data?.name || 'team')}`;
        }

        return describeAiActivityEvent(event);
    }

    function extractPluginAiMessages(data = {}) {
        return normalizePluginAiMessagesPayload(data);
    }

    function mergePluginAiMessages(existing = [], incoming = []) {
        const merged = [];
        const seen = new Set();
        [...(Array.isArray(existing) ? existing : []), ...(Array.isArray(incoming) ? incoming : [])].forEach((message) => {
            if (!message || typeof message !== 'object') return;
            const id = message.id != null ? `id:${String(message.id)}` : null;
            const fallback = `tmp:${String(message.role || '')}:${String(message.created_at || '')}:${String(message.content || '')}`;
            const key = id || fallback;
            if (seen.has(key)) return;
            seen.add(key);
            merged.push(message);
        });
        return merged;
    }

    function capturePluginAiMessages(messages = []) {
        const state = window.getPluginAiState();
        state.messages = Array.isArray(messages) ? messages : [];
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ messages: state.messages });
        }
    }

    function pushPluginAiMessage(message = {}) {
        const state = window.getPluginAiState();
        state.messages = mergePluginAiMessages(state.messages || [], [message]);
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ messages: state.messages });
        }
        return state.messages;
    }

    function replacePendingAssistantMessage(message = {}) {
        const state = window.getPluginAiState();
        const messages = Array.isArray(state.messages) ? [...state.messages] : [];
        const pendingIndex = messages.findIndex((item) => item && item.is_pending_assistant);
        if (pendingIndex >= 0) {
            messages[pendingIndex] = message;
        } else {
            messages.push(message);
        }
        state.messages = mergePluginAiMessages([], messages);
        return state.messages;
    }

    function removePendingAssistantMessage() {
        const state = window.getPluginAiState();
        state.messages = (Array.isArray(state.messages) ? state.messages : []).filter((item) => !item?.is_pending_assistant);
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ messages: state.messages });
        }
        return state.messages;
    }

    function capturePluginAiToolAudit(messages = []) {
        const state = window.getPluginAiState();
        state.events = extractToolEventsFromMessages(messages);
    }

    function appendPluginAiLiveActivity(events = []) {
        const state = window.getPluginAiState();
        const nextEvents = Array.isArray(events) ? events.filter(Boolean) : [];
        state.liveActivity = [...(Array.isArray(state.liveActivity) ? state.liveActivity : []), ...nextEvents].slice(-100);
        if (typeof window.rememberPluginAiEventsSnapshot === 'function') {
            window.rememberPluginAiEventsSnapshot({
                plugin: state.plugin,
                threadId: state.threadId,
                isTheme: !!state.isTheme,
                events: state.liveActivity,
                createdAt: new Date().toISOString(),
            });
        }
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ liveActivity: state.liveActivity, events: state.events });
        }
        return state.liveActivity;
    }

    function applyPluginAiStreamChunk(chunk = {}) {
        const state = window.getPluginAiState();
        const type = String(chunk?.type || '').trim();
        const data = chunk?.data;

        if (type === 'runtime_event' && data) {
            appendPluginAiLiveActivity([data]);
        } else if (type === 'bridge_event' && data) {
            appendPluginAiLiveActivity([data]);
        } else if (type === 'pending_approval' && data && typeof data === 'object') {
            state.pendingApproval = data;
            if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                window.syncCurrentPluginAiThreadSnapshot({ pendingApproval: state.pendingApproval, sending: true });
            }
        } else if (type === 'user_message' && data) {
            const currentMessages = Array.isArray(state.messages) ? state.messages : [];
            const stableMessages = currentMessages.filter((item) => !String(item?.id || '').startsWith('tmp-user-') && !item?.is_pending_assistant);
            const pendingMessages = currentMessages.filter((item) => item?.is_pending_assistant);
            state.messages = mergePluginAiMessages(stableMessages, [data, ...pendingMessages]);
        } else if (type === 'final' && data && typeof data === 'object') {
            const messages = [];
            if (data.user_message) messages.push(data.user_message);
            if (data.assistant_message) messages.push(data.assistant_message);
            const withoutPending = (state.messages || []).filter((item) => !item?.is_pending_assistant);
            state.messages = mergePluginAiMessages(withoutPending, messages);
            state.events = Array.isArray(data.team_events) ? data.team_events : [];
            state.liveActivity = state.events.length ? state.events : (state.liveActivity || []);
            state.pendingApproval = data.pending_approval && typeof data.pending_approval === 'object'
                ? data.pending_approval
                : null;
            if (typeof window.rememberPluginAiEventsSnapshot === 'function') {
                window.rememberPluginAiEventsSnapshot({
                    plugin: state.plugin,
                    threadId: state.threadId,
                    isTheme: !!state.isTheme,
                    events: state.liveActivity,
                    createdAt: new Date().toISOString(),
                });
            }
            if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                window.syncCurrentPluginAiThreadSnapshot({
                    messages: state.messages,
                    events: state.events,
                    liveActivity: state.liveActivity,
                    sending: false,
                });
            }
            if (data.thread && typeof window.replacePluginAiThreadInState === 'function') {
                window.replacePluginAiThreadInState(data.thread);
                if (typeof window.rememberPluginAiThread === 'function') {
                    window.rememberPluginAiThread(data.thread);
                }
            }
        }
        return state;
    }

    function buildPluginAiSessionLabel(thread = {}, index = 0) {
        const title = String(thread.title || '').trim();
        const pluginSlug = String(thread.plugin_slug || '').trim();
        if (title) {
            if (pluginSlug && title === pluginSlug) {
                return 'Chat 1';
            }
            if (pluginSlug) {
                const escapedSlug = pluginSlug.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const match = title.match(new RegExp(`^${escapedSlug} Chat (\\d+)$`, 'i'));
                if (match) {
                    return `Chat ${match[1]}`;
                }
            }
            return title;
        }
        const position = Number(index || 0) + 1;
        return `Chat ${position}`;
    }

    function buildPluginAiSessionMeta(thread = {}) {
        const updatedAt = String(thread.updated_at || thread.created_at || '').trim();
        return updatedAt || 'No activity yet';
    }

    function getActivePluginAiThread() {
        const state = window.getPluginAiState();
        return Array.isArray(state.threads)
            ? state.threads.find((item) => Number(item?.id || 0) === Number(state.threadId || 0)) || null
            : null;
    }

    function getPluginAiSourceStatus() {
        const state = window.getPluginAiState();
        const activeThread = getActivePluginAiThread();
        const fallback = state.sourceStatus && typeof state.sourceStatus === 'object' ? state.sourceStatus : {};
        const sourceAvailable = !!(activeThread?.source_available ?? fallback.source_available);
        const contextMode = String(activeThread?.source_context_mode || fallback.source_context_mode || 'metadata_only');
        const sourcePath = String(activeThread?.source_path || fallback.source_path || '');
        const workspacePath = String(activeThread?.workspace_path || fallback.workspace_path || sourcePath || '');
        return {
            source_available: sourceAvailable,
            source_context_mode: contextMode,
            source_path: sourcePath,
            workspace_path: workspacePath,
        };
    }

    function renderPluginAiSourceStatusCard() {
        const state = window.getPluginAiState();
        const source = getPluginAiSourceStatus();
        const sourceCard = document.getElementById('plugin-ai-source-card');
        const sourceAvailability = document.getElementById('plugin-ai-source-availability');
        const sourceContext = document.getElementById('plugin-ai-source-context');
        const sourcePath = document.getElementById('plugin-ai-source-path');
        const sourceButton = document.getElementById('plugin-ai-source-download-btn');
        if (!sourceCard || !sourceAvailability || !sourceContext || !sourcePath || !sourceButton) return;

        const hasAssistantHistory = Array.isArray(state.messages)
            && state.messages.some((item) => String(item?.role || '') === 'assistant' && !item?.is_pending_assistant);
        sourceCard.classList.toggle('is-hidden', hasAssistantHistory && !state.sourcePreparing);

        sourceAvailability.textContent = source.source_available ? 'Ready' : 'Not downloaded';
        sourceContext.textContent = source.source_context_mode === 'attached'
            ? 'Attached'
            : (source.source_context_mode === 'available' ? 'Available' : 'Metadata-only');
        sourcePath.textContent = shortenPluginAiPath(source.source_path || '', { workspaceRoot: source.workspace_path || '' }) || '—';
        sourceButton.textContent = state.sourcePreparing
            ? 'Preparing...'
            : (source.source_available ? 'Re-download' : 'Download');
        sourceButton.disabled = !!state.sourcePreparing;
    }

    function renderInlineMarkdown(text = '') {
        const tokens = [];
        let html = escapeHtml(String(text || ''));

        html = html.replace(/`([^`]+)`/g, (_, code) => {
            const token = `@@INLINE_CODE_${tokens.length}@@`;
            tokens.push(`<code>${escapeHtml(code)}</code>`);
            return token;
        });

        html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
        html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');
        html = html.replace(/(^|\W)\*([^*]+)\*(?=\W|$)/g, '$1<em>$2</em>');
        html = html.replace(/(^|\W)_([^_]+)_(?=\W|$)/g, '$1<em>$2</em>');

        tokens.forEach((value, index) => {
            html = html.replace(`@@INLINE_CODE_${index}@@`, value);
        });
        return html;
    }

    function renderMarkdownTableRow(line = '') {
        const trimmed = String(line || '').trim().replace(/^\|/, '').replace(/\|$/, '');
        return trimmed.split('|').map((cell) => renderInlineMarkdown(cell.trim()));
    }

    function isMarkdownTableSeparator(line = '') {
        const trimmed = String(line || '').trim();
        return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed);
    }

    function normalizeMarkdownParagraphLines(lines = []) {
        const parts = [];
        (Array.isArray(lines) ? lines : []).forEach((line) => {
            const value = String(line || '').trim();
            if (!value) return;
            if (!parts.length) {
                parts.push(value);
                return;
            }
            if (/^[,.;:!?%)\]\}]+$/.test(value)) {
                parts[parts.length - 1] += value;
                return;
            }
            if (/^[,.;:!?%)\]\}]/.test(value)) {
                parts[parts.length - 1] += value;
                return;
            }
            if (/^["'”’]/.test(value)) {
                parts[parts.length - 1] += ` ${value}`;
                return;
            }
            parts.push(value);
        });

        return parts.reduce((output, part) => {
            if (!output) return part;
            if (/[\s([{-]$/.test(output)) return `${output}${part}`;
            if (/^[,.;:!?%)\]\}]/.test(part)) return `${output}${part}`;
            return `${output} ${part}`;
        }, '');
    }

    function renderParagraphBlock(lines = []) {
        const text = normalizeMarkdownParagraphLines(lines);
        return text ? `<p>${renderInlineMarkdown(text)}</p>` : '';
    }

    function shouldMergeParagraphBreak(_paragraphLines = [], _nextLine = '') {
        return false;
    }

    function renderListBlock(lines = [], type = 'ul') {
        const tag = type === 'ol' ? 'ol' : 'ul';
        const items = lines
            .map((line) => String(line || '').trim())
            .map((line) => line.replace(type === 'ol' ? /^\d+\.\s+/ : /^[-*+]\s+/, ''))
            .map((line) => `<li>${renderInlineMarkdown(normalizeMarkdownParagraphLines([line]))}</li>`)
            .join('');
        return items ? `<${tag}>${items}</${tag}>` : '';
    }

    function renderBlockquoteBlock(lines = []) {
        const content = renderParagraphBlock(lines.map((line) => String(line || '').replace(/^>\s?/, '')));
        return content ? `<blockquote>${content}</blockquote>` : '';
    }

    function renderTableBlock(lines = []) {
        if (lines.length < 2) return renderParagraphBlock(lines);
        const header = renderMarkdownTableRow(lines[0]);
        const rows = lines.slice(2).map((line) => renderMarkdownTableRow(line));
        return `
            <div class="plugin-ai-table-wrap">
                <table>
                    <thead><tr>${header.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead>
                    <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
                </table>
            </div>
        `;
    }

    function normalizeFindingFieldKey(value = '') {
        return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
    }

    function findingSeverityTone(value = '') {
        const severity = String(value || '').trim().toLowerCase();
        if (severity === 'critical') return 'critical';
        if (severity === 'high') return 'high';
        if (severity === 'medium') return 'medium';
        if (severity === 'low') return 'low';
        return 'info';
    }

    function escapeFindingAttr(value = '') {
        return escapeHtml(String(value || '').trim().toLowerCase());
    }

    function parsePluginAiFindingBlocks(source = '') {
        const raw = String(source || '').replace(/\r\n/g, '\n');
        if (!raw.trim()) return [];

        const lines = raw.split('\n');
        const findings = [];
        let current = null;
        let currentListField = '';

        const ensureCurrent = (title = '') => {
            if (!current) {
                current = {
                    title: String(title || '').trim(),
                    severity: '',
                    confidence: '',
                    impact: '',
                    exploitability: '',
                    evidence: [],
                    affected_files: [],
                    recommended_fix: [],
                    notes: [],
                };
            }
            return current;
        };

        const pushCurrent = () => {
            if (!current || !String(current.title || '').trim()) return;
            findings.push({ ...current });
            current = null;
            currentListField = '';
        };

        lines.forEach((rawLine) => {
            const line = String(rawLine || '');
            const trimmed = line.trim();

            const findingMatch = trimmed.match(/^##\s+Finding:\s*(.+)$/i);
            if (findingMatch) {
                pushCurrent();
                current = {
                    title: findingMatch[1].trim(),
                    severity: '',
                    confidence: '',
                    impact: '',
                    exploitability: '',
                    evidence: [],
                    affected_files: [],
                    recommended_fix: [],
                    notes: [],
                };
                currentListField = '';
                return;
            }

            if (!current) return;
            if (!trimmed) return;

            const fieldMatch = trimmed.match(/^[-*]\s+([^:]+):\s*(.*)$/);
            if (fieldMatch) {
                const key = normalizeFindingFieldKey(fieldMatch[1]);
                const value = String(fieldMatch[2] || '').trim();
                currentListField = '';

                if (key === 'severity' || key === 'confidence' || key === 'impact' || key === 'exploitability') {
                    current[key] = value;
                    return;
                }

                if (key === 'evidence' || key === 'affected_files' || key === 'recommended_fix' || key === 'notes') {
                    currentListField = key;
                    if (value) current[key].push(value);
                    return;
                }
            }

            const nestedBulletMatch = trimmed.match(/^[-*]\s+(.+)$/);
            if (nestedBulletMatch && currentListField && Array.isArray(current[currentListField])) {
                current[currentListField].push(nestedBulletMatch[1].trim());
                return;
            }

            if (currentListField && Array.isArray(current[currentListField])) {
                current[currentListField].push(trimmed);
                return;
            }

            current.notes.push(trimmed);
        });

        pushCurrent();
        return findings.filter((item) => String(item.title || '').trim());
    }

    function renderPluginAiFindingCards(source = '') {
        const findings = parsePluginAiFindingBlocks(source);
        if (!findings.length) return '';

        const cards = findings.map((finding) => {
            const severity = String(finding.severity || 'Info').trim() || 'Info';
            const confidence = String(finding.confidence || 'Unknown').trim() || 'Unknown';
            const impact = String(finding.impact || '').trim();
            const exploitability = String(finding.exploitability || '').trim();
            const evidence = Array.isArray(finding.evidence) ? finding.evidence.filter(Boolean) : [];
            const affectedFiles = Array.isArray(finding.affected_files) ? finding.affected_files.filter(Boolean) : [];
            const fixes = Array.isArray(finding.recommended_fix) ? finding.recommended_fix.filter(Boolean) : [];
            const notes = Array.isArray(finding.notes) ? finding.notes.filter(Boolean) : [];
            const tone = findingSeverityTone(severity);

            return `
                <article class="plugin-ai-finding-card" data-severity="${escapeFindingAttr(tone)}">
                    <div class="plugin-ai-finding-card-head">
                        <div>
                            <div class="plugin-ai-finding-kicker">Security finding</div>
                            <h3>${renderInlineMarkdown(finding.title)}</h3>
                        </div>
                        <div class="plugin-ai-finding-badges">
                            <span class="plugin-ai-finding-badge severity-${escapeFindingAttr(tone)}">${escapeHtml(severity)}</span>
                            <span class="plugin-ai-finding-badge confidence">${escapeHtml(confidence)} confidence</span>
                        </div>
                    </div>
                    <div class="plugin-ai-finding-grid">
                        ${impact ? `<section><strong>Impact</strong><p>${renderInlineMarkdown(impact)}</p></section>` : ''}
                        ${exploitability ? `<section><strong>Exploitability</strong><p>${renderInlineMarkdown(exploitability)}</p></section>` : ''}
                        ${evidence.length ? `<section><strong>Evidence</strong><ul>${evidence.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul></section>` : ''}
                        ${affectedFiles.length ? `<section><strong>Affected files</strong><ul>${affectedFiles.map((item) => `<li><code>${escapeHtml(item)}</code></li>`).join('')}</ul></section>` : ''}
                        ${fixes.length ? `<section><strong>Recommended fix</strong><ul>${fixes.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul></section>` : ''}
                        ${notes.length ? `<section><strong>Notes</strong><ul>${notes.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul></section>` : ''}
                    </div>
                </article>
            `;
        }).join('');

        return `<div class="plugin-ai-findings">${cards}</div>`;
    }

    function renderPluginAiMarkdown(source = '') {
        const raw = String(source || '').replace(/\r\n/g, '\n');
        if (!raw.trim()) return '';

        const findingCardsHtml = renderPluginAiFindingCards(raw);
        const codeBlocks = [];
        const withPlaceholders = raw.replace(/```([\w-]*)\n([\s\S]*?)```/g, (_, language, code) => {
            const index = codeBlocks.length;
            codeBlocks.push({ language: String(language || '').trim(), code: String(code || '').replace(/\n$/, '') });
            return `\n@@CODEBLOCK_${index}@@\n`;
        });

        const lines = withPlaceholders.split('\n');
        const html = [];
        let index = 0;

        while (index < lines.length) {
            const line = String(lines[index] || '');
            const trimmed = line.trim();

            if (!trimmed) {
                index += 1;
                continue;
            }

            const codeMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
            if (codeMatch) {
                const block = codeBlocks[Number(codeMatch[1])] || { language: '', code: '' };
                const languageAttr = block.language ? ` data-language="${escapeHtml(block.language)}"` : '';
                const languageBadge = block.language ? `<span class="plugin-ai-code-lang">${escapeHtml(block.language)}</span>` : '';
                html.push(`<pre class="plugin-ai-code-block"${languageAttr}>${languageBadge}<code>${escapeHtml(block.code)}</code></pre>`);
                index += 1;
                continue;
            }

            if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
                html.push('<hr>');
                index += 1;
                continue;
            }

            const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
            if (headingMatch) {
                const level = Math.min(6, headingMatch[1].length);
                html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2].trim())}</h${level}>`);
                index += 1;
                continue;
            }

            if (trimmed.startsWith('>')) {
                const quoteLines = [];
                while (index < lines.length && String(lines[index] || '').trim().startsWith('>')) {
                    quoteLines.push(String(lines[index] || '').trim());
                    index += 1;
                }
                html.push(renderBlockquoteBlock(quoteLines));
                continue;
            }

            if (trimmed.includes('|') && index + 1 < lines.length && isMarkdownTableSeparator(lines[index + 1])) {
                const tableLines = [trimmed, String(lines[index + 1] || '').trim()];
                index += 2;
                while (index < lines.length) {
                    const row = String(lines[index] || '').trim();
                    if (!row || !row.includes('|')) break;
                    tableLines.push(row);
                    index += 1;
                }
                html.push(renderTableBlock(tableLines));
                continue;
            }

            if (/^\d+\.\s+/.test(trimmed)) {
                const listLines = [];
                while (index < lines.length && /^\d+\.\s+/.test(String(lines[index] || '').trim())) {
                    listLines.push(String(lines[index] || '').trim());
                    index += 1;
                }
                html.push(renderListBlock(listLines, 'ol'));
                continue;
            }

            if (/^[-*+]\s+/.test(trimmed)) {
                const listLines = [];
                while (index < lines.length && /^[-*+]\s+/.test(String(lines[index] || '').trim())) {
                    listLines.push(String(lines[index] || '').trim());
                    index += 1;
                }
                html.push(renderListBlock(listLines, 'ul'));
                continue;
            }

            const paragraphLines = [];
            while (index < lines.length) {
                const current = String(lines[index] || '');
                const currentTrimmed = current.trim();

                if (!currentTrimmed) {
                    let lookahead = index + 1;
                    while (lookahead < lines.length && !String(lines[lookahead] || '').trim()) {
                        lookahead += 1;
                    }
                    const nextTrimmed = lookahead < lines.length ? String(lines[lookahead] || '').trim() : '';
                    if (shouldMergeParagraphBreak(paragraphLines, nextTrimmed)) {
                        index = lookahead;
                        continue;
                    }
                    break;
                }

                if (/^@@CODEBLOCK_\d+@@$/.test(currentTrimmed)) break;
                if (/^(#{1,6})\s+/.test(currentTrimmed)) break;
                if (/^(-{3,}|\*{3,}|_{3,})$/.test(currentTrimmed)) break;
                if (currentTrimmed.startsWith('>')) break;
                if (/^\d+\.\s+/.test(currentTrimmed)) break;
                if (/^[-*+]\s+/.test(currentTrimmed)) break;
                if (currentTrimmed.includes('|') && index + 1 < lines.length && isMarkdownTableSeparator(lines[index + 1])) break;
                paragraphLines.push(currentTrimmed);
                index += 1;
            }
            html.push(renderParagraphBlock(paragraphLines));
        }

        const markdownHtml = html.filter(Boolean).join('');
        return `${findingCardsHtml || ''}${markdownHtml}`;
    }

    function renderPluginAiSessions(threads = [], activeThreadId = null) {
        const container = document.getElementById('plugin-ai-sessions');
        if (!container) return;

        if (!Array.isArray(threads) || threads.length === 0) {
            container.innerHTML = '<div class="plugin-ai-session-empty">No chats yet.</div>';
            return;
        }

        container.innerHTML = threads
            .map((thread, index) => {
                const id = Number(thread.id || 0);
                const activeClass = id === Number(activeThreadId || 0) ? ' is-active' : '';
                const state = typeof window.getPluginAiState === 'function' ? window.getPluginAiState() : {};
                const snapshot = typeof window.getPluginAiThreadUiSnapshot === 'function'
                    ? window.getPluginAiThreadUiSnapshot(String(thread.plugin_slug || state.plugin || '').trim(), id, !!thread.is_theme)
                    : null;
                const isRunning = !!snapshot?.sending;
                const runDuration = isRunning && typeof window.formatPluginAiRunDuration === 'function'
                    ? window.formatPluginAiRunDuration(snapshot?.runStartedAt)
                    : '';
                const runningMeta = isRunning
                    ? `<span class="plugin-ai-session-running"><span class="plugin-ai-session-running-dot"></span>Running${runDuration ? ` • ${escapeHtml(runDuration)}` : ''}</span>`
                    : '';
                return `
                    <div class="plugin-ai-session-item${activeClass}${isRunning ? ' is-running' : ''}" data-thread-id="${id}">
                        <button type="button" class="plugin-ai-session-main" data-thread-id="${id}">
                            <strong>${escapeHtml(buildPluginAiSessionLabel(thread, index))}</strong>
                            <span>${escapeHtml(buildPluginAiSessionMeta(thread))}</span>
                            ${runningMeta}
                        </button>
                        <div class="plugin-ai-session-actions">
                            <button type="button" class="plugin-ai-session-icon" data-thread-rename="${id}" title="Rename chat" aria-label="Rename chat">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
                            </button>
                            <button type="button" class="plugin-ai-session-icon is-danger" data-thread-delete="${id}" title="Delete chat" aria-label="Delete chat">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path></svg>
                            </button>
                        </div>
                    </div>
                `;
            })
            .join('');
    }

    function updatePluginAiSessionUi() {
        const state = window.getPluginAiState();
        renderPluginAiSessions(state.threads || [], state.threadId);
    }

    function setPluginAiMessagesEmptyView() {
        renderPluginAiMessages([]);
    }

    function setPluginAiActivityEmptyView() {
        renderPluginAiActivity([]);
    }

    function getPluginAiVisibleActivityEntries(entries = [], expanded = false) {
        const safeEntries = Array.isArray(entries) ? entries : [];
        if (expanded) return safeEntries;
        return safeEntries.slice(-3);
    }

    function escapePluginAiAttr(value = '') {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function pluginAiToolBadgeTone(toolName = '') {
        const tool = String(toolName || '').trim().toLowerCase();
        if (tool === 'bash') return 'bash';
        if (tool === 'read' || tool === 'file_read') return 'read';
        if (tool === 'grep') return 'grep';
        if (tool === 'write' || tool === 'file_write') return 'write';
        if (tool === 'edit' || tool === 'file_edit') return 'edit';
        return 'neutral';
    }

    function extractPluginAiDecisionTrace(events = []) {
        const safeEvents = Array.isArray(events) ? events : [];
        for (let index = safeEvents.length - 1; index >= 0; index -= 1) {
            const event = safeEvents[index];
            const type = String(event?.type || '');
            const data = event?.data && typeof event.data === 'object' ? event.data : {};
            if (type === 'decision_trace') {
                return data;
            }
            if (type === 'intent_resolved' && data.decision_trace && typeof data.decision_trace === 'object') {
                return data.decision_trace;
            }
        }
        return {};
    }

    function buildPluginAiTraceSummary(events = []) {
        const trace = extractPluginAiDecisionTrace(events);
        const normalized = trace.normalized_decision && typeof trace.normalized_decision === 'object'
            ? trace.normalized_decision
            : trace;
        return {
            trace,
            normalized,
            reason: String(normalized.reason || trace.reason || ''),
            strategy: String(normalized.strategy || trace.strategy || ''),
            executionMode: String(normalized.execution_mode || trace.execution_mode || ''),
            teamMode: String(normalized.team_mode || trace.team_mode || ''),
            compositionSource: String(trace.composition_source || normalized.composition_source || ''),
            needsTools: normalized.needs_tools ?? trace.needs_tools,
            securityFocus: normalized.security_focus ?? trace.security_focus,
        };
    }

    function buildPluginAiExecutionDetailItems(events = []) {
        const safeEvents = Array.isArray(events) ? events : [];
        const state = window.getPluginAiState ? window.getPluginAiState() : {};
        const workspaceRoot = String(state?.liveActivityOptions?.workspaceRoot || '').trim();
        const items = [];

        safeEvents.forEach((event) => {
            const type = String(event?.type || '').trim();
            if (type !== 'tool_call') return;

            const data = event?.data && typeof event.data === 'object' ? event.data : {};
            const tool = String(data.name || data.toolName || data.tool || '').trim();
            const input = data.input && typeof data.input === 'object' ? data.input : data;

            if (tool === 'bash') {
                const commandRaw = String(input.command || data.command || '').trim();
                const command = truncatePluginAiText(commandRaw, 140);
                items.push({
                    label: 'Tool call • bash',
                    value: command || '(no command)',
                    copyText: commandRaw || undefined,
                });
                return;
            }

            if (tool === 'read' || tool === 'file_read') {
                const path = shortenPluginAiPath(String(input.path || data.path || '').trim(), { workspaceRoot });
                items.push({ label: `Tool call • ${tool || 'read'}`, value: path || '(no path)' });
                return;
            }

            if (tool === 'grep') {
                const pattern = shortenPluginAiPattern(String(input.pattern || '').trim());
                const path = shortenPluginAiPath(String(input.path || data.path || '').trim(), { workspaceRoot }) || '.';
                items.push({
                    label: 'Tool call • grep',
                    value: [pattern ? `pattern: ${pattern}` : '', `path: ${path}`].filter(Boolean).join(' • ') || '(no input)',
                });
                return;
            }

            if (tool === 'write' || tool === 'file_write' || tool === 'edit' || tool === 'file_edit') {
                const path = shortenPluginAiPath(String(input.path || data.path || '').trim(), { workspaceRoot });
                items.push({ label: `Tool call • ${tool}`, value: path || '(no path)' });
                return;
            }

            const fallbackValue = truncatePluginAiText(JSON.stringify(input), 180);
            items.push({ label: `Tool call${tool ? ` • ${tool}` : ''}`, value: fallbackValue || '(no input)' });
        });

        return items;
    }

    function buildPluginAiExecutionSummary(events = []) {
        const safeEvents = Array.isArray(events) ? events : [];
        const agents = new Set();
        const tools = new Set();
        let bashCount = 0;

        safeEvents.forEach((event) => {
            const type = String(event?.type || '');
            const data = event?.data && typeof event.data === 'object' ? event.data : {};
            if (type === 'agent_started' || type === 'agent_completed') {
                const name = String(data.name || '').trim();
                if (name) agents.add(name);
            }
            if (type === 'tool_call') {
                const tool = String(data.name || data.toolName || data.tool || '').trim();
                if (tool) tools.add(tool);
                if (tool === 'bash') bashCount += 1;
            }
        });

        const details = buildPluginAiExecutionDetailItems(safeEvents);
        return {
            totalEvents: details.length,
            agents: [...agents],
            tools: [...tools],
            bashCount,
            details,
        };
    }

    function renderPluginAiActivityRail(entries = [], options = {}) {
        const expanded = !!options.expanded;
        const visibleEntries = getPluginAiVisibleActivityEntries(entries, expanded);
        const toggleLabel = expanded ? 'Show less' : `Show all activity (${entries.length})`;
        const subtitle = expanded
            ? `${entries.length} events visible`
            : `${Math.min(entries.length, 3)} of ${entries.length} events visible`;

        return `
            <div class="plugin-ai-live-activity" aria-live="polite">
                <div class="plugin-ai-live-activity-head plugin-ai-live-activity-head--space-between">
                    <div class="plugin-ai-live-activity-title-wrap">
                        <span>Working</span>
                        <span class="plugin-ai-live-activity-dots"><i></i><i></i><i></i></span>
                    </div>
                    ${entries.length > 3 ? `<button type="button" class="plugin-ai-inline-toggle" data-plugin-ai-toggle="activityExpanded">${escapeHtml(toggleLabel)}</button>` : ''}
                </div>
                <div class="plugin-ai-live-activity-subhead">${escapeHtml(subtitle)}</div>
                <div class="plugin-ai-live-activity-rail${expanded ? ' is-expanded' : ''}">
                    ${visibleEntries
                        .map((entry, index) => `
                            <div class="plugin-ai-live-activity-item${entry.isCurrent ? ' is-current' : ''}${index === visibleEntries.length - 1 ? ' is-latest' : ' is-history'}" data-activity-type="${escapeHtml(entry.type)}" data-tone="${escapeHtml(entry.tone || 'neutral')}" data-category="${escapeHtml(entry.category || 'activity')}">
                                <div class="plugin-ai-activity-row-head">
                                    <em class="plugin-ai-activity-icon" aria-hidden="true">${escapeHtml(entry.icon || '•')}</em>
                                    <strong>${escapeHtml(entry.label)}</strong>
                                    ${entry.count > 1 ? `<small>×${escapeHtml(String(entry.count))}</small>` : ''}
                                    ${entry.bashCommand ? `<button type="button" class="plugin-ai-copy-btn plugin-ai-copy-btn--icon" data-copy-label="⧉" data-copy-text="${escapePluginAiAttr(entry.bashCommand)}" aria-label="Copy command" title="Copy command">⧉</button>` : ''}
                                    ${entry.isCurrent ? '<mark>Now</mark>' : '<mark class="is-history">Past</mark>'}
                                </div>
                                ${entry.detail ? `<span>${escapeHtml(entry.detail)}</span>` : ''}
                            </div>
                        `)
                        .join('')}
                </div>
            </div>
        `;
    }

    function renderPluginAiDecisionTracePanel(events = []) {
        const summary = buildPluginAiTraceSummary(events);

        const normalizedTeam = String(summary.teamMode || '').trim().toLowerCase();
        const compactLine = [
            summary.strategy ? `Strategy: ${summary.strategy}` : '',
            (summary.teamMode && normalizedTeam !== 'single_agent') ? `Team: ${summary.teamMode}` : '',
            typeof summary.needsTools === 'boolean' ? `Tools: ${summary.needsTools ? 'on' : 'off'}` : '',
        ].filter(Boolean).join(' • ');

        if (!compactLine) {
            return '';
        }

        return `
            <section class="plugin-ai-decision-trace">
                <div class="plugin-ai-execution-summary-head">
                    <div>
                        <strong>Run info</strong>
                        <p>${escapeHtml(compactLine)}</p>
                    </div>
                </div>
            </section>
        `;
    }

    function formatPluginAiApprovalModeLabel(mode = '') {
        const normalized = String(mode || '').trim().toLowerCase();
        if (normalized === 'manual') return 'Manual approval';
        if (normalized === 'auto_approve') return 'Auto approve';
        if (normalized === 'off') return 'Approval off (YOLO • Dangerous)';
        return normalized || 'Unknown';
    }

    function formatPluginAiApprovalTaskLabel(task = {}, fallbackIndex = 0) {
        if (!task || typeof task !== 'object') return `Task ${fallbackIndex + 1}`;
        return String(task.title || task.id || `Task ${fallbackIndex + 1}`).trim() || `Task ${fallbackIndex + 1}`;
    }

    function formatPluginAiApprovalTaskMeta(task = {}) {
        if (!task || typeof task !== 'object') return '';
        const status = String(task.status || '').trim();
        const assignee = String(task.assignee || '').trim();
        const id = String(task.id || '').trim();
        return [
            status ? `status: ${status}` : '',
            assignee ? `assignee: ${assignee}` : '',
            id ? `id: ${id}` : '',
        ].filter(Boolean).join(' • ');
    }

    function buildPluginAiApprovalScopeSummary(events = [], requestPayload = {}) {
        const safeEvents = Array.isArray(events) ? events : [];
        const toolCalls = [];

        safeEvents.forEach((event) => {
            const type = String(event?.type || '').trim();
            if (type !== 'tool_call') return;
            const data = event?.data && typeof event.data === 'object' ? event.data : {};
            const input = data.input && typeof data.input === 'object' ? data.input : data;
            const name = String(data.name || data.toolName || data.tool || '').trim();
            if (!name) return;
            toolCalls.push({ name, input });
        });

        const uniqueTools = [...new Set(toolCalls.map((call) => call.name))];
        const bashCommands = toolCalls
            .filter((call) => call.name === 'bash')
            .map((call) => String(call.input?.command || '').trim())
            .filter(Boolean);
        const readTargets = toolCalls
            .filter((call) => call.name === 'read' || call.name === 'file_read')
            .map((call) => String(call.input?.path || '').trim())
            .filter(Boolean);

        const completedTasks = Array.isArray(requestPayload.completedTasks) ? requestPayload.completedTasks : [];
        const nextTasks = Array.isArray(requestPayload.nextTasks) ? requestPayload.nextTasks : [];

        const scope = String(requestPayload.scope || '').trim();
        const toolName = String(requestPayload.toolName || '').trim();
        const toolInput = requestPayload.toolInput && typeof requestPayload.toolInput === 'object'
            ? requestPayload.toolInput
            : null;
        const riskLevel = String(requestPayload.riskLevel || '').trim();
        const riskReason = String(requestPayload.riskReason || '').trim();
        const summary = String(requestPayload.summary || '').trim();

        return {
            toolCallCount: toolCalls.length,
            uniqueTools,
            bashCommands,
            readTargets,
            completedTasks,
            nextTasks,
            scope,
            toolName,
            toolInput,
            riskLevel,
            riskReason,
            summary,
        };
    }

    function renderPluginAiStructuredOutput(message = {}) {
        const structured = message && typeof message.structured === 'object' ? message.structured : null;
        if (!structured) return '';
        return `
            <section class="plugin-ai-execution-summary is-expanded">
                <div class="plugin-ai-execution-summary-head">
                    <div>
                        <strong>Structured output</strong>
                        <p>Validated JSON returned by Open Multi-Agent</p>
                    </div>
                </div>
                <div class="plugin-ai-execution-summary-details">
                    <div class="plugin-ai-execution-detail-row">
                        <strong>JSON</strong>
                        <span>${escapeHtml(JSON.stringify(structured, null, 2))}</span>
                    </div>
                </div>
            </section>
        `;
    }

    function renderPluginAiApprovalCard(pendingApproval = null, events = []) {
        if (!pendingApproval || typeof pendingApproval !== 'object' || String(pendingApproval.status || '') !== 'pending') {
            return '';
        }

        const requestPayload = pendingApproval.request_payload && typeof pendingApproval.request_payload === 'object'
            ? pendingApproval.request_payload
            : {};
        const scopeSummary = buildPluginAiApprovalScopeSummary(events, requestPayload);
        const nextTasks = scopeSummary.nextTasks;
        const completedTasks = scopeSummary.completedTasks;
        const modeLabel = formatPluginAiApprovalModeLabel(pendingApproval.mode || requestPayload.mode || 'manual');

        const toolsLine = scopeSummary.uniqueTools.length ? scopeSummary.uniqueTools.join(', ') : 'No tool metadata available';
        const latestBash = scopeSummary.bashCommands.length ? scopeSummary.bashCommands[scopeSummary.bashCommands.length - 1] : '';
        const latestRead = scopeSummary.readTargets.length ? scopeSummary.readTargets[scopeSummary.readTargets.length - 1] : '';

        const scope = String(scopeSummary.scope || '').trim();
        const toolName = String(scopeSummary.toolName || '').trim();
        const riskLevel = String(scopeSummary.riskLevel || '').trim();
        const riskReason = String(scopeSummary.riskReason || '').trim();
        const summaryText = String(scopeSummary.summary || '').trim();
        const toolInput = scopeSummary.toolInput && typeof scopeSummary.toolInput === 'object' ? scopeSummary.toolInput : null;
        const pendingCommand = toolName === 'bash' ? String(toolInput?.command || '').trim() : '';
        const pendingPath = toolInput && typeof toolInput.path === 'string' ? String(toolInput.path).trim() : '';

        const nextTaskRows = nextTasks.length
            ? nextTasks
                .slice(0, 4)
                .map((task, index) => {
                    const label = formatPluginAiApprovalTaskLabel(task, index);
                    const meta = formatPluginAiApprovalTaskMeta(task);
                    return `<li><strong>${escapeHtml(label)}</strong>${meta ? `<span>${escapeHtml(meta)}</span>` : ''}</li>`;
                })
                .join('')
            : '<li><strong>No next task details supplied.</strong><span>The runtime requested approval without detailed task metadata.</span></li>';

        const isToolScope = scope === 'tool_call';
        const headingText = isToolScope ? 'Tool approval required' : 'Manual approval required';
        const subtitleText = isToolScope
            ? 'Review the requested command before continuing.'
            : 'This run is paused before continuing the pipeline.';

        const toolToneClass = toolName ? `tone-${String(toolName).toLowerCase().replace(/[^a-z0-9_-]+/g, '-')}` : '';
        const conciseActionText = (() => {
            if (toolName === 'write' && pendingPath) return `write ${shortenPluginAiPath(pendingPath)}`;
            if (toolName === 'edit' && pendingPath) return `edit ${shortenPluginAiPath(pendingPath)}`;
            if (toolName === 'read' && pendingPath) return `read ${shortenPluginAiPath(pendingPath)}`;
            if (toolName === 'bash' && pendingCommand) return pendingCommand;
            if (pendingPath) return `${toolName || 'tool'} ${shortenPluginAiPath(pendingPath)}`;
            if (summaryText) return summaryText;
            return toolName || 'Tool call';
        })();
        const toolScopeCard = isToolScope
            ? `
                <div class="plugin-ai-approval-card">
                    <div class="plugin-ai-approval-card__top">
                        <div>
                            <div class="plugin-ai-approval-card__eyebrow">Pending action</div>
                            <div class="plugin-ai-approval-card__title">${escapeHtml(summaryText || 'A tool call needs your approval.')}</div>
                        </div>
                        <span class="plugin-ai-tool-badge ${escapeHtml(toolToneClass)}">${escapeHtml(toolName || 'tool')}</span>
                    </div>
                    <div class="plugin-ai-approval-command">${escapeHtml(conciseActionText)}</div>
                    ${pendingPath && toolName !== 'bash' ? `<div class="plugin-ai-approval-meta"><span>Target</span><code>${escapeHtml(shortenPluginAiPath(pendingPath))}</code></div>` : ''}
                    ${riskLevel ? `<div class="plugin-ai-approval-meta"><span>Risk</span><strong>${escapeHtml(riskLevel)}${riskReason ? ` • ${escapeHtml(riskReason)}` : ''}</strong></div>` : ''}
                </div>
              `
            : '';

        const primaryRows = isToolScope
            ? toolScopeCard
            : `
                    <div class="plugin-ai-execution-detail-row"><strong>Approve will</strong><span>Continue pending tasks with the same tools for this run.</span></div>
                    <div class="plugin-ai-execution-detail-row"><strong>Reject will</strong><span>Stop the run and mark it as failed.</span></div>
                    <div class="plugin-ai-execution-detail-row"><strong>Tools used so far</strong><span>${escapeHtml(toolsLine)}</span></div>
                    ${latestBash ? `<div class="plugin-ai-execution-detail-row has-copy"><strong>Latest bash command</strong><span>${escapeHtml(truncatePluginAiText(latestBash, 220))}</span><button type="button" class="plugin-ai-copy-btn plugin-ai-copy-btn--inline" data-copy-text="${escapePluginAiAttr(latestBash)}">Copy</button></div>` : ''}
                    ${latestRead ? `<div class="plugin-ai-execution-detail-row"><strong>Latest read target</strong><span>${escapeHtml(shortenPluginAiPath(latestRead))}</span></div>` : ''}
                    <div class="plugin-ai-execution-detail-row"><strong>Upcoming tasks</strong><span>Review the next queued tasks below before you approve.</span></div>
              `;

        return `
            <section class="plugin-ai-execution-summary is-expanded${isToolScope ? ' is-tool-approval' : ''}">
                <div class="plugin-ai-execution-summary-head">
                    <div>
                        <strong>${escapeHtml(headingText)}</strong>
                        ${subtitleText ? `<p>${escapeHtml(subtitleText)}</p>` : ''}
                    </div>
                </div>
                ${isToolScope ? '' : `<div class="plugin-ai-summary-chips">
                    <span class="plugin-ai-summary-chip">mode: ${escapeHtml(modeLabel)}</span>
                    <span class="plugin-ai-summary-chip">tool calls: ${escapeHtml(String(scopeSummary.toolCallCount))}</span>
                    <span class="plugin-ai-summary-chip">completed: ${escapeHtml(String(completedTasks.length))}</span>
                    <span class="plugin-ai-summary-chip">next: ${escapeHtml(String(nextTasks.length))}</span>
                </div>`}
                <div class="plugin-ai-execution-summary-details${isToolScope ? ' is-tool-approval' : ''}">
                    ${primaryRows}
                </div>
                ${isToolScope ? '' : `<div class="plugin-ai-approval-task-block">
                    <ul class="plugin-ai-approval-task-list">${nextTaskRows}</ul>
                </div>`}
                <div class="plugin-ai-approval-actions${isToolScope ? ' is-tool-approval' : ''}">
                    <button type="button" class="secondary-btn plugin-ai-approval-btn plugin-ai-approval-btn--approve" id="plugin-ai-approve-run">Approve</button>
                    <button type="button" class="danger-btn plugin-ai-approval-btn plugin-ai-approval-btn--reject" id="plugin-ai-reject-run">Reject</button>
                </div>
            </section>
        `;
    }

    function renderPluginAiExecutionSummary(events = [], options = {}) {
        const expanded = !!options.expanded;
        const summary = buildPluginAiExecutionSummary(events);
        if (!summary.totalEvents) return '';

        const detailRows = summary.details.length
            ? summary.details.map((item) => `
                <div class="plugin-ai-execution-detail-row${item.copyText ? ' has-copy' : ''}">
                    <strong>${escapeHtml(item.label)}</strong>
                    <span>${escapeHtml(item.value)}</span>
                    ${item.copyText ? `<button type="button" class="plugin-ai-copy-btn plugin-ai-copy-btn--inline" data-copy-text="${escapePluginAiAttr(item.copyText)}">Copy</button>` : ''}
                </div>
            `)
            : [`<div class="plugin-ai-execution-detail-row"><strong>Execution details</strong><span>No execution events were captured for this run.</span></div>`];

        return `
            <section class="plugin-ai-execution-summary${expanded ? ' is-expanded' : ''}">
                <div class="plugin-ai-execution-summary-head">
                    <div>
                        <strong>Execution summary</strong>
                        <p>${escapeHtml(summary.agents.length)} agent • ${escapeHtml(summary.tools.length)} tool • ${escapeHtml(String(summary.bashCount))} bash</p>
                    </div>
                    <button type="button" class="plugin-ai-inline-toggle" data-plugin-ai-toggle="summaryExpanded">${expanded ? 'Hide details' : 'View details'}</button>
                </div>
                <div class="plugin-ai-summary-chips">
                    <span class="plugin-ai-summary-chip">${escapeHtml(String(summary.totalEvents))} events</span>
                    ${summary.agents.length > 1 ? summary.agents.slice(0, 3).map((agent) => `<span class="plugin-ai-summary-chip">${escapeHtml(agent)}</span>`).join('') : ''}
                    ${summary.tools.slice(0, 3).map((tool) => `<span class="plugin-ai-summary-chip">${escapeHtml(tool)}</span>`).join('')}
                </div>
                ${expanded ? `<div class="plugin-ai-execution-summary-details">${detailRows.join('')}</div>` : ''}
                ${renderPluginAiDecisionTracePanel(events)}
            </section>
        `;
    }

    function bindPluginAiInlineToggles(container) {
        if (!container || container.dataset.inlineTogglesBound === '1') return;
        container.addEventListener('click', async (event) => {
            const copyButton = event.target.closest('[data-copy-text]');
            if (copyButton) {
                const text = String(copyButton.getAttribute('data-copy-text') || '').trim();
                const defaultLabelAttr = String(copyButton.getAttribute('data-copy-label') || '').trim();
                if (!copyButton.dataset.copyDefaultLabel) {
                    copyButton.dataset.copyDefaultLabel = defaultLabelAttr || String(copyButton.textContent || '').trim() || 'Copy';
                }
                const fallbackLabel = String(copyButton.dataset.copyDefaultLabel || 'Copy').trim() || 'Copy';
                if (text) {
                    try {
                        if (navigator?.clipboard?.writeText) {
                            await navigator.clipboard.writeText(text);
                        }
                        copyButton.textContent = defaultLabelAttr ? '✓' : 'Copied';
                        window.setTimeout(() => {
                            copyButton.textContent = fallbackLabel;
                        }, 1200);
                    } catch (_error) {
                        copyButton.textContent = defaultLabelAttr ? '⚠' : 'Copy failed';
                        window.setTimeout(() => {
                            copyButton.textContent = fallbackLabel;
                        }, 1400);
                    }
                }
                return;
            }

            const button = event.target.closest('[data-plugin-ai-toggle]');
            if (!button) return;
            const key = String(button.getAttribute('data-plugin-ai-toggle') || '').trim();
            if (!key || typeof window.togglePluginAiUiFlag !== 'function') return;
            window.togglePluginAiUiFlag(key);
            refreshPluginAiRenderedState();
        });
        container.dataset.inlineTogglesBound = '1';
    }

    function renderPluginAiMessages(messages = []) {
        const container = document.getElementById('plugin-ai-messages');
        if (!container) return;

        const state = window.getPluginAiState();
        const uiState = typeof window.ensurePluginAiUiState === 'function'
            ? window.ensurePluginAiUiState()
            : { activityExpanded: false, summaryExpanded: false };
        const activityEntries = buildPluginAiActivityEntries(state.liveActivity || state.events || [], state.liveActivityOptions || {});
        const distanceFromBottom = Math.max(0, container.scrollHeight - container.scrollTop - container.clientHeight);
        const shouldStickToBottom = distanceFromBottom <= 40;

        if (!Array.isArray(messages) || messages.length === 0) {
            container.innerHTML = '';
            container.dataset.renderSignature = '';
            return;
        }

        bindPluginAiInlineToggles(container);

        const latestAssistantIndex = [...messages].map((message, index) => ({ message, index })).reverse().find((item) => String(item.message?.role || 'assistant') !== 'user' && !item.message?.is_pending_assistant)?.index ?? -1;

        const nextHtml = messages
            .map((message, index) => {
                const role = String(message.role || 'assistant');
                const roleLabel = role === 'user' ? 'You' : 'AI';
                const isPendingAssistant = !!message.is_pending_assistant;
                const roleClass = `${role === 'user' ? ' is-user' : ''}${isPendingAssistant ? ' is-pending' : ''}`;
                const content = isPendingAssistant ? '' : String(message.content || '');
                const cachedEventsSnapshot = isPendingAssistant && typeof window.getPluginAiEventsSnapshot === 'function'
                    ? window.getPluginAiEventsSnapshot(state.plugin, state.threadId, !!state.isTheme)
                    : null;
                const cachedEntries = isPendingAssistant && Array.isArray(cachedEventsSnapshot?.events)
                    ? buildPluginAiActivityEntries(cachedEventsSnapshot.events, state.liveActivityOptions || {})
                    : [];
                const pendingEntries = activityEntries.length ? activityEntries : cachedEntries;
                const bodyHtml = isPendingAssistant
                    ? `
                        ${pendingEntries.length
                            ? renderPluginAiActivityRail(pendingEntries, { expanded: !!uiState.activityExpanded })
                            : `
                            <div class="plugin-ai-live-activity plugin-ai-live-activity--compact" aria-live="polite">
                                <div class="plugin-ai-live-activity-head">
                                    <span class="plugin-ai-live-activity-dots"><i></i><i></i><i></i></span>
                                </div>
                            </div>
                        `}
                        ${state.pendingApproval ? renderPluginAiApprovalCard(state.pendingApproval, state.events || state.liveActivity || []) : ''}
                    `
                    : `
                        <div class="plugin-ai-markdown">${renderPluginAiMarkdown(content)}</div>
                        ${role !== 'user' ? renderPluginAiStructuredOutput(message) : ''}
                        ${role !== 'user' && index === latestAssistantIndex ? renderPluginAiApprovalCard(state.pendingApproval, state.events || state.liveActivity || []) : ''}
                        ${role !== 'user' && index === latestAssistantIndex ? renderPluginAiExecutionSummary(state.events || state.liveActivity || [], { expanded: !!uiState.summaryExpanded }) : ''}
                    `;
                return `
                    <article class="plugin-ai-message${roleClass}">
                        <strong>${escapeHtml(roleLabel)}</strong>
                        ${bodyHtml}
                    </article>
                `;
            })
            .join('');

        const renderSignature = JSON.stringify({
            messageCount: messages.length,
            latestAssistantIndex,
            latestMessageId: messages[messages.length - 1]?.id || '',
            latestMessageContent: String(messages[messages.length - 1]?.content || ''),
            pendingCount: messages.filter((item) => item?.is_pending_assistant).length,
            eventCount: Array.isArray(state.events) ? state.events.length : 0,
            liveActivityCount: Array.isArray(state.liveActivity) ? state.liveActivity.length : 0,
            activityExpanded: !!uiState.activityExpanded,
            summaryExpanded: !!uiState.summaryExpanded,
            traceExpanded: !!uiState.traceExpanded,
        });

        if (container.dataset.renderSignature !== renderSignature) {
            container.innerHTML = nextHtml;
            container.dataset.renderSignature = renderSignature;
        }

        if (shouldStickToBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }

    function renderPluginAiActivity(events = []) {
        return renderPluginAiActivityRail(buildPluginAiActivityEntries(events), { expanded: true });
    }

    function refreshPluginAiRenderedState() {
        const state = window.getPluginAiState();
        renderPluginAiSourceStatusCard();
        renderPluginAiMessages(state.messages || []);
    }

    function updatePluginAiThreadsAfterMessage(threadId) {
        const state = window.getPluginAiState();
        const threads = Array.isArray(state.threads) ? state.threads : [];
        const threadIndex = threads.findIndex((item) => Number(item.id || 0) === Number(threadId || 0));
        if (threadIndex < 0) return;
        const [thread] = threads.splice(threadIndex, 1);
        thread.updated_at = new Date().toISOString();
        state.threads = [thread, ...threads];
        updatePluginAiSessionUi();
    }

    function replacePluginAiThreadInState(updatedThread = {}) {
        const state = window.getPluginAiState();
        const threads = Array.isArray(state.threads) ? [...state.threads] : [];
        const index = threads.findIndex((item) => Number(item.id || 0) === Number(updatedThread.id || 0));
        if (index < 0) return;
        threads[index] = { ...threads[index], ...updatedThread };
        state.threads = threads;
        updatePluginAiSessionUi();
    }

    function removePluginAiThreadFromState(threadId) {
        const state = window.getPluginAiState();
        const threads = Array.isArray(state.threads) ? state.threads.filter((item) => Number(item.id || 0) !== Number(threadId || 0)) : [];
        state.threads = threads;
        updatePluginAiSessionUi();
    }

    window.normalizePluginAiInput = normalizePluginAiInput;
    window.sanitizePluginAiMessageInput = sanitizePluginAiMessageInput;
    window.normalizePluginAiMessagesPayload = normalizePluginAiMessagesPayload;
    window.extractToolEventsFromMessages = extractToolEventsFromMessages;
    window.buildPluginAiActivityEntries = buildPluginAiActivityEntries;
    window.describeAiActivityEvent = describeAiActivityEvent;
    window.formatPluginAiActivity = formatPluginAiActivity;
    window.extractPluginAiMessages = extractPluginAiMessages;
    window.mergePluginAiMessages = mergePluginAiMessages;
    window.capturePluginAiMessages = capturePluginAiMessages;
    window.pushPluginAiMessage = pushPluginAiMessage;
    window.replacePendingAssistantMessage = replacePendingAssistantMessage;
    window.removePendingAssistantMessage = removePendingAssistantMessage;
    window.capturePluginAiToolAudit = capturePluginAiToolAudit;
    window.appendPluginAiLiveActivity = appendPluginAiLiveActivity;
    window.applyPluginAiStreamChunk = applyPluginAiStreamChunk;
    window.buildPluginAiSessionLabel = buildPluginAiSessionLabel;
    window.buildPluginAiSessionMeta = buildPluginAiSessionMeta;
    window.getPluginAiSourceStatus = getPluginAiSourceStatus;
    window.renderPluginAiSourceStatusCard = renderPluginAiSourceStatusCard;
    window.renderInlineMarkdown = renderInlineMarkdown;
    window.renderPluginAiMarkdown = renderPluginAiMarkdown;
    window.renderPluginAiSessions = renderPluginAiSessions;
    window.updatePluginAiSessionUi = updatePluginAiSessionUi;
    window.setPluginAiMessagesEmptyView = setPluginAiMessagesEmptyView;
    window.setPluginAiActivityEmptyView = setPluginAiActivityEmptyView;
    window.renderPluginAiMessages = renderPluginAiMessages;
    window.renderPluginAiActivity = renderPluginAiActivity;
    window.refreshPluginAiRenderedState = refreshPluginAiRenderedState;
    window.updatePluginAiThreadsAfterMessage = updatePluginAiThreadsAfterMessage;
    window.replacePluginAiThreadInState = replacePluginAiThreadInState;
    window.removePluginAiThreadFromState = removePluginAiThreadFromState;
})();
