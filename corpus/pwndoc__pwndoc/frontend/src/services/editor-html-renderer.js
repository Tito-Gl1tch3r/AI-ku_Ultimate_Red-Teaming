import Utils from '@/services/utils'

function renderLegendText(label, alt) {
  return [label, alt].filter(Boolean).join(' - ')
}

export function resolveEditorImageSrc(src) {
  return /^[a-fA-F0-9]{24}$/.test(src || '')
    ? `/api/images/download/${src}`
    : src
}

// Parses `html` into a document, lets `transform` mutate it in place, and
// serializes the result back out. Shared by normalize/denormalize below since
// both are "parse, rewrite some elements, re-serialize" passes.
function transformHtml(html, transform) {
  const clean = String(html || '')
  if (!clean) return ''

  const doc = new DOMParser().parseFromString(clean, 'text/html')
  transform(doc)
  return doc.body.innerHTML
}

export function normalizeEditorHtml(html) {
  return transformHtml(Utils.htmlEncode(String(html || '')), (doc) => {
    doc.body.querySelectorAll('legend').forEach((legend) => {
      const label = legend.getAttribute('label') || ''
      const alt = legend.getAttribute('alt') || ''
      const visibleCaption = renderLegendText(label, alt)
      if (visibleCaption && !legend.textContent.trim()) {
        legend.textContent = visibleCaption
      }
      legend.removeAttribute('label')
      legend.removeAttribute('alt')
      legend.removeAttribute('commentid')
    })

    doc.body.querySelectorAll('img').forEach((img) => {
      const figure = doc.createElement('figure')
      const normalizedImg = doc.createElement('img')
      const caption = doc.createElement('figcaption')
      const alt = img.getAttribute('alt') || ''

      figure.className = 'draft-image'
      normalizedImg.setAttribute('src', resolveEditorImageSrc(img.getAttribute('src') || ''))
      normalizedImg.setAttribute('alt', '')
      caption.textContent = alt

      figure.appendChild(normalizedImg)
      if (alt) figure.appendChild(caption)
      img.replaceWith(figure)
    })
  })
}

// Inverse of the image transform in normalizeEditorHtml. Used when a user selects
// a fragment of the rendered draft preview (which contains download URLs and
// figure/figcaption wrappers) so the applied content carries image ids again.
export function denormalizeEditorHtml(html) {
  return transformHtml(html, (doc) => {
    doc.body.querySelectorAll('figure.draft-image').forEach((figure) => {
      const img = figure.querySelector('img')
      if (!img) {
        figure.remove()
        return
      }

      const caption = figure.querySelector('figcaption')
      const src = img.getAttribute('src') || ''
      const match = src.match(/\/api\/images\/download\/([a-fA-F0-9]{24})$/)
      const id = match ? match[1] : src

      const normalizedImg = doc.createElement('img')
      normalizedImg.setAttribute('src', id)
      normalizedImg.setAttribute('alt', caption?.textContent || '')

      figure.replaceWith(normalizedImg)
    })
  })
}
