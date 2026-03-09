/* glossary.js — Click-to-open popovers for DOCSIS term explanations */

(function () {
  'use strict';

  // Single shared popover appended to body (escapes overflow:hidden + transform)
  var overlay = document.createElement('div');
  overlay.className = 'glossary-popover';
  document.body.appendChild(overlay);

  var activeHint = null;

  function closeAll() {
    overlay.style.display = 'none';
    overlay.classList.remove('above');
    if (activeHint) {
      activeHint.classList.remove('open');
      activeHint = null;
    }
  }

  function showPopover(hint) {
    var source = hint.querySelector('.glossary-popover');
    if (!source) return;
    overlay.textContent = source.textContent;
    overlay.style.display = 'block';
    overlay.classList.remove('above');

    var r = hint.getBoundingClientRect();
    var top = r.bottom + 8;
    var left = r.left + r.width / 2;
    overlay.style.left = left + 'px';
    overlay.style.top = top + 'px';
    overlay.style.transform = 'translateX(-50%)';

    // Flip above if near bottom
    var popRect = overlay.getBoundingClientRect();
    if (popRect.bottom > window.innerHeight - 20) {
      overlay.classList.add('above');
      overlay.style.top = (r.top - 8) + 'px';
      overlay.style.transform = 'translateX(-50%) translateY(-100%)';
    }
  }

  document.addEventListener('click', function (e) {
    // Ignore clicks on the overlay itself
    if (e.target === overlay) return;

    var hint = e.target.closest('.glossary-hint');
    if (hint) {
      e.preventDefault();
      e.stopPropagation();
      var wasOpen = hint === activeHint;
      closeAll();
      if (!wasOpen) {
        activeHint = hint;
        hint.classList.add('open');
        showPopover(hint);
      }
      return;
    }
    closeAll();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll();
  });
})();
