import type { SiteReport, TechStack, SocialLink, RedFlag, Subdomain, AssetNode } from '../types';
import { techRules, socialPatterns } from './rules';

export function analyzeHtml(html: string, finalUrl: string, domain: string): Partial<SiteReport> {
  // We use a regex-based approach here so it works without a full DOM if needed,
  // but in the browser we can use DOMParser.
  // For maximum compatibility across server (cheerio) and client, 
  // we'll pass in an object that implements a basic query selector.

  const titleMatch = html.match(/<title>(.*?)<\/title>/i);
  const title = titleMatch ? titleMatch[1] : '';

  const descMatch = html.match(/<meta[^>]*name=["']description["'][^>]*content=["'](.*?)["']/i) || 
                   html.match(/<meta[^>]*content=["'](.*?)["'][^>]*name=["']description["']/i);
  const description = descMatch ? descMatch[1] : '';

  const langMatch = html.match(/<html[^>]*lang=["'](.*?)["']/i);
  const language = langMatch ? langMatch[1] : 'en';

  const themeMatch = html.match(/<meta[^>]*name=["']theme-color["'][^>]*content=["'](.*?)["']/i);
  const themeColor = themeMatch ? themeMatch[1] : '';

  // Extract Heading structure
  const h1Count = (html.match(/<h1\b/gi) || []).length;
  const h2Count = (html.match(/<h2\b/gi) || []).length;
  const h3Count = (html.match(/<h3\b/gi) || []).length;

  // Extract Fonts (Enhanced detection)
  const fonts: string[] = [];
  
  // 1. Google Fonts
  const googleFontMatches = html.match(/(?:family=)([^&"'>\s]+)/g);
  if (googleFontMatches) {
    googleFontMatches.forEach(f => {
      const name = f.replace('family=', '').replace(/\+/g, ' ').split(':')[0].trim();
      if (name && !fonts.includes(name)) fonts.push(name);
    });
  }

  // 2. Adobe Fonts (Typekit)
  const adobeFontMatches = html.match(/use\.typekit\.net\/([^.]+)\.css/g);
  if (adobeFontMatches) {
    // Adobe fonts are usually loaded via a kit ID, but we can search for the font-family in the CSS if we had it.
    // For now, we'll mark it as a generic "Adobe Fonts" or try to find font-family in the same HTML
    fonts.push('Adobe Font');
  }

  // 3. CSS font-family (in style tags or inline)
  const cssFontMatches = html.match(/font-family\s*:\s*([^;!}\n]+)/gi);
  if (cssFontMatches) {
    cssFontMatches.forEach(match => {
      const name = match.split(':')[1].split(',').map(f => f.replace(/["']/g, '').trim());
      const commonSystem = ['inherit', 'initial', 'unset', 'sans-serif', 'serif', 'monospace', 'cursive', 'fantasy', 'system-ui', '-apple-system', 'blinkmacsystemfont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Verdana', 'Georgia', 'Times New Roman', 'Trebuchet MS'];
      
      for (let n of name) {
        // Validation: No hashes, no weird technical names, no too short/long
        const isHash = /^[a-f0-9.-]{8,}$/i.test(n) || /[0-9]{5,}/.test(n);
        const isTooShort = n.length < 3;
        const isTooLong = n.length > 40;
        const isTechnical = n.includes('.') || n.includes('_') || n.includes('#');

        if (n && !fonts.includes(n) && !isHash && !isTooShort && !isTooLong && !isTechnical && 
            !commonSystem.some(sys => n.toLowerCase() === sys.toLowerCase())) {
          fonts.push(n);
          break;
        }
      }
    });
  }

  // 4. @font-face detection
  const fontFaceMatches = html.match(/font-family\s*:\s*["']?([^;,"'}]+)["']?\s*;\s*src/gi);
  if (fontFaceMatches) {
    fontFaceMatches.forEach(match => {
      const name = match.split(':')[1].split(';')[0].replace(/["']/g, '').trim();
      if (name && !fonts.includes(name)) fonts.push(name);
    });
  }


  // Tech Stack
  const techStack: TechStack[] = [];
  for (const rule of techRules) {
    if (rule.pattern.test(html)) {
      techStack.push({ 
        name: rule.name, 
        category: rule.category, 
        website: rule.website || `https://www.google.com/search?q=${encodeURIComponent(rule.name)}`
      });
    }
  }

  // Social Links
  const socialLinks: SocialLink[] = [];
  for (const sp of socialPatterns) {
    const match = html.match(new RegExp(`href=["']([^"']?${sp.pattern.source}[^"']?)["']`, 'i'));
    if (match && !socialLinks.find(l => l.platform === sp.platform)) {
      socialLinks.push({ platform: sp.platform, url: match[1] });
    }
  }

  // Colors
  const brandColors: string[] = [];
  const hexMatch = html.match(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g);
  if (hexMatch) {
    const uniqueHex = Array.from(new Set(hexMatch))
      .filter(c => {
        const lower = c.toLowerCase();
        return !['#ffffff', '#000000', '#fff', '#000', '#f3f4f6', '#111827', '#1f2937', '#374151', '#4b5563', '#6b7280', '#9ca3af', '#d1d5db', '#e5e7eb', '#f9fafb'].includes(lower);
      })
      .slice(0, 5);
    brandColors.push(...uniqueHex);
  }

  return {
    title,
    description,
    techStack,
    socialLinks,
    brandColors: brandColors.length > 0 ? brandColors : ['#000000', '#ffffff'],
    language,
    themeColor,
    headings: { h1: h1Count, h2: h2Count, h3: h3Count },
    fonts: fonts.slice(0, 5)
  };
}
