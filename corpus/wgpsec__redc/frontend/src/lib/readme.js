export function parseReadmeMarkdown(md, templateName) {
  if (!md) return '';

  function isResolvedAssetUrl(url) {
    return /^(?:[a-z]+:|\/\/|\/)/i.test(url);
  }

  const placeholders = [];

  function protect(html) {
    const id = `\x00PH${placeholders.length}\x00`;
    placeholders.push(html);
    return id;
  }

  function restore(text) {
    let previous;
    do {
      previous = text;
      placeholders.forEach((html, index) => {
        text = text.replaceAll(`\x00PH${index}\x00`, html);
      });
    } while (text !== previous);
    return text;
  }

  function escapeHtml(value) {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  md = md.replace(/```([a-z]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const escaped = escapeHtml(code.trimEnd());
    return protect(`<pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-3 text-[12px] font-mono leading-relaxed"><code>${escaped}</code></pre>`);
  });

  md = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  md = md.replace(/`([^`]+)`/g, (_, code) => {
    return protect(`<code class="bg-gray-100 px-1.5 py-0.5 rounded text-[12px] font-mono text-pink-600">${code}</code>`);
  });

  md = md.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
    const safeAlt = alt || '';
    let resolvedUrl = url;

    if (templateName && !isResolvedAssetUrl(url)) {
      const baseParts = templateName.split('/');
      const imageParts = url.split('/');
      const resolved = [...baseParts];

      for (const part of imageParts) {
        if (part === '..') {
          resolved.pop();
        } else if (part !== '.') {
          resolved.push(part);
        }
      }

      resolvedUrl = `https://raw.githubusercontent.com/wgpsec/redc-template/master/${resolved.join('/')}`;
    }

    return protect(`<img src="${resolvedUrl}" alt="${safeAlt}" class="max-w-full rounded-lg my-3" onerror="this.style.display='none'">`);
  });

  md = md.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => {
    return protect(`<a href="${url}" class="text-blue-600 hover:text-blue-800 hover:underline underline-offset-2" target="_blank" rel="noopener">${text}</a>`);
  });

  md = md.replace(/^#### (.*$)/gm, '<h4 class="text-sm font-semibold mt-5 mb-2 text-gray-800">$1</h4>');
  md = md.replace(/^### (.*$)/gm, '<h3 class="text-sm font-semibold mt-5 mb-2 text-gray-800">$1</h3>');
  md = md.replace(/^## (.*$)/gm, '<h2 class="text-base font-bold mt-6 mb-3 text-gray-900">$1</h2>');
  md = md.replace(/^# (.*$)/gm, '<h1 class="text-lg font-bold mt-6 mb-3 text-gray-900">$1</h1>');

  md = md.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
  md = md.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
  md = md.replace(/\*(.*?)\*/g, '<em>$1</em>');
  md = md.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>');
  md = md.replace(/__(.+?)__/g, '<strong class="font-semibold">$1</strong>');
  md = md.replace(/(?<!\w)_([^_]+)_(?!\w)/g, '<em>$1</em>');

  md = md.replace(/^&gt; (.*$)/gm, '<blockquote class="border-l-4 border-gray-300 pl-4 py-1 my-1 text-gray-600 italic">$1</blockquote>');
  md = md.replace(/(<\/blockquote>)\n(<blockquote[^>]*>)/g, '<br>');

  const tableBlocks = [];
  let tableIndex = 0;

  md = md.replace(/(^\|.+\|[ \t]*\n\|[\s:|-]+\|[ \t]*\n(\|.+\|[ \t]*\n?)*)/gm, (match) => {
    const lines = match.trim().split('\n').filter((line) => line.trim());
    if (lines.length < 2) return match;

    const headerCells = lines[0]
      .split('|')
      .filter((_, index, array) => index > 0 && index < array.length - 1)
      .map((cell) => cell.trim());
    const separators = lines[1]
      .split('|')
      .filter((_, index, array) => index > 0 && index < array.length - 1)
      .map((cell) => cell.trim());
    const aligns = separators.map((separator) => {
      if (separator.startsWith(':') && separator.endsWith(':')) return 'center';
      if (separator.endsWith(':')) return 'right';
      return 'left';
    });

    const tableHead = headerCells.map((cell, index) => {
      return `<th class="px-3 py-2 text-left text-[11px] font-semibold text-gray-900 bg-gray-50" style="text-align:${aligns[index] || 'left'}">${cell}</th>`;
    }).join('');

    const tableBody = lines.slice(2).map((line) => {
      const cells = line
        .split('|')
        .filter((_, index, array) => index > 0 && index < array.length - 1)
        .map((cell) => cell.trim());
      const columns = cells.map((cell, index) => {
        return `<td class="px-3 py-2 text-[12px] text-gray-700 border-t border-gray-100" style="text-align:${aligns[index] || 'left'}">${cell}</td>`;
      }).join('');
      return `<tr class="hover:bg-gray-50/50">${columns}</tr>`;
    }).join('');

    const tableHtml = `<div class="my-3 overflow-x-auto rounded-lg border border-gray-200"><table class="w-full border-collapse text-[12px]"><thead><tr>${tableHead}</tr></thead><tbody>${tableBody}</tbody></table></div>`;
    const placeholder = `__TABLE_${tableIndex}__`;
    tableBlocks.push(tableHtml);
    tableIndex += 1;
    return placeholder;
  });

  md = md.replace(/^---$/gm, '<hr class="my-6 border-gray-200">');
  md = md.replace(/^\*\*\*$/gm, '<hr class="my-6 border-gray-200">');
  md = md.replace(/^(?:\* |- )(.*$)/gm, '<li class="ml-4 list-disc text-gray-700">$1</li>');
  md = md.replace(/^\d+\. (.*$)/gm, '<li class="ml-4 list-decimal text-gray-700">$1</li>');
  md = md.replace(/<\/li>\n<li/g, '</li><li');
  md = md.replace(/<\/li>\s*<br>/g, '</li>');
  md = md.replace(/<br>\s*<li/g, '<li');

  md = md.replace(/(<li[^>]*>[\s\S]*?<\/li>)+/g, (match) => {
    const sanitized = match.replace(/<br\s*\/?>/g, '');
    if (sanitized.includes('list-disc')) {
      return `<ul class="my-2">${sanitized}</ul>`;
    }
    return `<ol class="my-2 list-inside">${sanitized}</ol>`;
  });

  const paragraphs = md.split(/\n\n+/);
  let result = paragraphs.map((paragraph) => {
    const trimmed = paragraph.trim();
    if (!trimmed) return '';
    if (trimmed.match(/^<(h[1-4]|ul|ol|pre|blockquote|hr|div)/i)) return trimmed;
    if (trimmed.match(/^__TABLE_\d+__$/) || trimmed.match(/^\x00PH\d+\x00$/)) return trimmed;
    return `<p class="my-2 text-gray-700 leading-relaxed">${trimmed.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  tableBlocks.forEach((html, index) => {
    result = result.replace(`__TABLE_${index}__`, html);
  });

  return restore(result);
}

export function handleReadmeLinkClick(event, openUrl) {
  const link = event.target.closest('a[href]');
  if (!link) return;

  event.preventDefault();
  if (typeof openUrl === 'function') {
    openUrl(link.href);
    return;
  }

  window.open(link.href, '_blank', 'noopener');
}