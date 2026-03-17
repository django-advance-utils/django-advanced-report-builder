$(document).ready(function () {
    var raw = sessionStorage.getItem('record_nav')
    if (!raw) return

    var data
    try {
        data = JSON.parse(raw)
    } catch (e) {
        sessionStorage.removeItem('record_nav')
        return
    }

    // currentIndex is set by the datatable click handler
    var currentIndex = data.currentIndex
    if (currentIndex === undefined || currentIndex < 0) {
        sessionStorage.removeItem('record_nav')
        return
    }

    var urls = data.urls || []
    var referrer = data.referrer || ''
    var title = data.title || ''

    // If we're back on the referrer page, clear and stop
    var refA = document.createElement('a')
    refA.href = referrer
    if (refA.pathname === window.location.pathname) {
        sessionStorage.removeItem('record_nav')
        return
    }

    var total = urls.length
    var position = currentIndex + 1
    var prevUrl = currentIndex > 0 ? urls[currentIndex - 1] : null
    var nextUrl = currentIndex < total - 1 ? urls[currentIndex + 1] : null

    // Build nav bar using DOM APIs to avoid XSS
    var bar = document.createElement('div')
    bar.className = 'record-nav d-flex align-items-center justify-content-end px-3 py-1'
    bar.style.cssText = 'background-color:#f0f0f0; border-bottom:1px solid #ddd;'

    var prevBtn = document.createElement('button')
    prevBtn.className = 'btn btn-sm btn-outline-secondary record-nav-prev mr-1'
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>'
    if (!prevUrl) prevBtn.disabled = true
    bar.appendChild(prevBtn)

    var posSpan = document.createElement('span')
    posSpan.className = 'mx-1 small text-muted'
    posSpan.textContent = position + ' of ' + total
    bar.appendChild(posSpan)

    var nextBtn = document.createElement('button')
    nextBtn.className = 'btn btn-sm btn-outline-secondary record-nav-next mr-2'
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>'
    if (!nextUrl) nextBtn.disabled = true
    bar.appendChild(nextBtn)

    var backLink = document.createElement('a')
    backLink.href = referrer
    backLink.className = 'btn btn-sm btn-outline-secondary'
    var listIcon = document.createElement('i')
    listIcon.className = 'fas fa-list'
    backLink.appendChild(listIcon)
    backLink.appendChild(document.createTextNode(' ' + title))
    bar.appendChild(backLink)

    var closeBtn = document.createElement('button')
    closeBtn.className = 'btn btn-sm btn-outline-secondary record-nav-close ml-2'
    closeBtn.innerHTML = '<i class="fas fa-times"></i>'
    bar.appendChild(closeBtn)

    // Insert into placeholder if present, otherwise before main content
    var placeholder = document.getElementById('record-nav-placeholder')
    if (placeholder) {
        placeholder.appendChild(bar)
    } else {
        var main = document.querySelector('main[role="main"]')
        if (main) main.parentNode.insertBefore(bar, main)
    }

    // Navigate and update index in sessionStorage
    function navigate(url, newIndex) {
        data.currentIndex = newIndex
        sessionStorage.setItem('record_nav', JSON.stringify(data))
        window.location.href = url
    }

    // Button click handlers
    prevBtn.addEventListener('click', function () {
        if (prevUrl) navigate(prevUrl, currentIndex - 1)
    })
    nextBtn.addEventListener('click', function () {
        if (nextUrl) navigate(nextUrl, currentIndex + 1)
    })

    // Close button
    closeBtn.addEventListener('click', function () {
        sessionStorage.removeItem('record_nav')
        bar.remove()
    })

    // Keyboard shortcuts (when not in form elements)
    document.addEventListener('keydown', function (e) {
        var tag = e.target.tagName.toLowerCase()
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) {
            return
        }
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return
        if (e.key === 'ArrowLeft' && prevUrl) {
            navigate(prevUrl, currentIndex - 1)
        } else if (e.key === 'ArrowRight' && nextUrl) {
            navigate(nextUrl, currentIndex + 1)
        } else if (e.key === 'Escape') {
            sessionStorage.removeItem('record_nav')
            bar.remove()
        }
    })
})
