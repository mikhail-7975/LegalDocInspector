/**
 * Макет LegalDocInspector — без боевой логики.
 * Можно расширить для демо-переключения состояний pipeline.
 */
(function () {
  'use strict';

  document.documentElement.setAttribute('data-mock-ui', 'legaldocinspector-v1');

  // Пример: клик по кнопке «Войти» не уходит в сеть
  document.querySelectorAll('.login-card .btn--primary').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      console.info('[mock] Вход (без запроса к серверу)');
    });
  });

  // В реальном приложении здесь будет beforeunload (§4 FR-1)
  // window.addEventListener('beforeunload', ...);

  var layout = document.querySelector('.layout');
  var notifPanel = document.getElementById('backend-notifications-panel');
  var notifToggle = document.getElementById('backend-notifications-toggle');
  var notifLabel = notifToggle && notifToggle.querySelector('.notifications-panel__toggle-label');

  var toastStack = document.querySelector('.toast-stack');
  if (toastStack) {
    toastStack.addEventListener('click', function (e) {
      var closeBtn = e.target.closest('.toast__close');
      if (!closeBtn || !toastStack.contains(closeBtn)) return;
      var toast = closeBtn.closest('.toast');
      if (toast) toast.remove();
    });
  }

  var SPRAVKI_MAX_PER_DOCSET = 20;

  function cloneSpravkaEmptyRow() {
    var tpl = document.getElementById('tpl-spravka-row-empty');
    if (!tpl) return null;
    return document.importNode(tpl.content, true).querySelector('.file-row--spravka');
  }

  function cloneSpravkaLoadedRow(filename) {
    var tpl = document.getElementById('tpl-spravka-row-loaded');
    if (!tpl) return null;
    var row = document.importNode(tpl.content, true).querySelector('.file-row--spravka');
    var fn = row.querySelector('.spravka-filename');
    if (fn) fn.textContent = filename;
    return row;
  }

  function refreshSpravkiBlock(block) {
    if (!block) return;
    var list = block.querySelector('.docset-spravki__list');
    if (!list) return;
    var rows = list.querySelectorAll('.file-row--spravka');
    var addBtn = block.querySelector('.js-add-spravka');
    var n = rows.length;
    rows.forEach(function (row, idx) {
      var title = row.querySelector('.spravka-slot-title');
      if (title) title.textContent = 'Справка ' + (idx + 1);
      var rm = row.querySelector('.js-spravka-remove-slot');
      if (rm) rm.hidden = n <= 1;
    });
    if (addBtn) {
      var atLimit = n >= SPRAVKI_MAX_PER_DOCSET;
      addBtn.disabled = atLimit;
      addBtn.setAttribute('aria-disabled', atLimit ? 'true' : 'false');
    }
  }

  var spravkaInput = document.createElement('input');
  spravkaInput.type = 'file';
  spravkaInput.accept = '.xls,.xlsx,.xlsm';
  spravkaInput.setAttribute('aria-hidden', 'true');
  spravkaInput.style.position = 'fixed';
  spravkaInput.style.left = '-9999px';
  spravkaInput.style.opacity = '0';
  spravkaInput.style.pointerEvents = 'none';
  document.body.appendChild(spravkaInput);

  var spravkaTargetRow = null;

  spravkaInput.addEventListener('change', function () {
    var row = spravkaTargetRow;
    spravkaTargetRow = null;
    if (!row || !spravkaInput.files || !spravkaInput.files.length) {
      spravkaInput.value = '';
      return;
    }
    var name = spravkaInput.files[0].name;
    var block = row.closest('.docset-spravki');
    var loaded = cloneSpravkaLoadedRow(name);
    if (loaded) row.replaceWith(loaded);
    if (block) refreshSpravkiBlock(block);
    spravkaInput.value = '';
    console.info('[mock] Справка о задолженности: выбран файл', name);
  });

  document.addEventListener('click', function (e) {
    var addBtn = e.target.closest('.js-add-spravka');
    if (addBtn) {
      e.preventDefault();
      if (addBtn.disabled) return;
      var block = addBtn.closest('.docset-spravki');
      var list = block && block.querySelector('.docset-spravki__list');
      if (!list) return;
      if (list.querySelectorAll('.file-row--spravka').length >= SPRAVKI_MAX_PER_DOCSET) return;
      var empty = cloneSpravkaEmptyRow();
      if (!empty) return;
      list.appendChild(empty);
      refreshSpravkiBlock(block);
      return;
    }

    var pick = e.target.closest('.js-spravka-pick');
    if (pick) {
      e.preventDefault();
      var prow = pick.closest('.file-row--spravka');
      if (!prow) return;
      spravkaTargetRow = prow;
      spravkaInput.click();
      return;
    }

    var rmSlot = e.target.closest('.js-spravka-remove-slot');
    if (rmSlot && !rmSlot.hidden) {
      e.preventDefault();
      var rrow = rmSlot.closest('.file-row--spravka');
      var rblock = rrow && rrow.closest('.docset-spravki');
      var rlist = rblock && rblock.querySelector('.docset-spravki__list');
      if (!rrow || !rlist) return;
      if (rlist.querySelectorAll('.file-row--spravka').length <= 1) return;
      rrow.remove();
      refreshSpravkiBlock(rblock);
      return;
    }

    var delFile = e.target.closest('.js-spravka-delete-file');
    if (delFile) {
      var drow = delFile.closest('.file-row--spravka');
      if (!drow) return;
      e.preventDefault();
      var dblock = drow.closest('.docset-spravki');
      var emptyRow = cloneSpravkaEmptyRow();
      if (emptyRow) drow.replaceWith(emptyRow);
      if (dblock) refreshSpravkiBlock(dblock);
    }
  });

  document.querySelectorAll('.docset-spravki').forEach(refreshSpravkiBlock);

  if (layout && notifPanel && notifToggle) {
    notifToggle.addEventListener('click', function () {
      var collapsed = !notifPanel.classList.contains('notifications-panel--collapsed');
      notifPanel.classList.toggle('notifications-panel--collapsed', collapsed);
      layout.classList.toggle('layout--notif-collapsed', collapsed);
      notifToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      if (collapsed) {
        notifToggle.setAttribute('title', 'Развернуть панель');
        if (notifLabel) notifLabel.textContent = 'Развернуть панель уведомлений';
      } else {
        notifToggle.setAttribute('title', 'Свернуть панель');
        if (notifLabel) notifLabel.textContent = 'Свернуть панель уведомлений';
      }
    });
  }

  console.info(
    '[mock] Откройте index.html в браузере. Файлы: interface/index.html, css/app.css, js/mock.js'
  );
})();
