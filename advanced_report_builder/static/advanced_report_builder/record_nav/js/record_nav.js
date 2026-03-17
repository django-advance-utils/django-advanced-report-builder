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

    // Build nav bar — all controls right-aligned
    var html = '<div class="record-nav d-flex align-items-center justify-content-end px-3 py-1" style="background-color:#f0f0f0; border-bottom:1px solid #ddd;">'
    html += '<button class="btn btn-sm btn-outline-secondary record-nav-prev mr-1"'
    if (!prevUrl) html += ' disabled'
    html += '><i class="fas fa-chevron-left"></i></button>'
    html += '<span class="mx-1 small text-muted">' + position + ' of ' + total + '</span>'
    html += '<button class="btn btn-sm btn-outline-secondary record-nav-next mr-2"'
    if (!nextUrl) html += ' disabled'
    html += '><i class="fas fa-chevron-right"></i></button>'
    html += '<a href="' + referrer + '" class="btn btn-sm btn-outline-secondary">'
    html += '<i class="fas fa-list"></i> ' + title + '</a>'
    html += '<button class="btn btn-sm btn-outline-secondary record-nav-close ml-2">'
    html += '<i class="fas fa-times"></i></button>'
    html += '</div>'

    // Insert into placeholder if present, otherwise before main content
    var $placeholder = $('#record-nav-placeholder')
    if ($placeholder.length) {
        $placeholder.html(html)
    } else {
        $('main[role="main"]').before(html)
    }

    // Navigate and update index in sessionStorage
    function navigate(url, newIndex) {
        data.currentIndex = newIndex
        sessionStorage.setItem('record_nav', JSON.stringify(data))
        window.location.href = url
    }

    // Button click handlers
    $('.record-nav-prev').on('click', function () {
        if (prevUrl) navigate(prevUrl, currentIndex - 1)
    })
    $('.record-nav-next').on('click', function () {
        if (nextUrl) navigate(nextUrl, currentIndex + 1)
    })

    // Close button
    $('.record-nav-close').on('click', function () {
        sessionStorage.removeItem('record_nav')
        $('#record-nav-placeholder').empty()
        $('.record-nav').remove()
    })

    // Keyboard shortcuts (when not in form elements)
    $(document).on('keydown', function (e) {
        var tag = e.target.tagName.toLowerCase()
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || $(e.target).attr('contenteditable')) {
            return
        }
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return
        if (e.key === 'ArrowLeft' && prevUrl) {
            navigate(prevUrl, currentIndex - 1)
        } else if (e.key === 'ArrowRight' && nextUrl) {
            navigate(nextUrl, currentIndex + 1)
        }
    })
})
