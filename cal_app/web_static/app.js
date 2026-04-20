const state = {
  schedules: [],
  overdueSchedules: [],
  tasks: [],
  visibleSchedules: [],
  selectedKeys: new Set(),
  initializedFilters: false,
  busy: false,
};

const refs = {
  todayValue: document.querySelector("#todayValue"),
  taskCount: document.querySelector("#taskCount"),
  scheduleCount: document.querySelector("#scheduleCount"),
  overdueCount: document.querySelector("#overdueCount"),
  scheduleBody: document.querySelector("#scheduleBody"),
  overdueBody: document.querySelector("#overdueBody"),
  overdueEmpty: document.querySelector("#overdueEmpty"),
  taskBody: document.querySelector("#taskBody"),
  taskEditForm: document.querySelector("#taskEditForm"),
  taskEditTitle: document.querySelector("#taskEditTitle"),
  editTaskId: document.querySelector("#editTaskId"),
  editTaskKind: document.querySelector("#editTaskKind"),
  editName: document.querySelector("#editName"),
  editDescription: document.querySelector("#editDescription"),
  editOneTimeFields: document.querySelector("#editOneTimeFields"),
  editRecurringFields: document.querySelector("#editRecurringFields"),
  editStartDate: document.querySelector("#editStartDate"),
  editEndDate: document.querySelector("#editEndDate"),
  editFirstStartDate: document.querySelector("#editFirstStartDate"),
  editFirstEndDate: document.querySelector("#editFirstEndDate"),
  editTaskStartDate: document.querySelector("#editTaskStartDate"),
  editTaskEndDate: document.querySelector("#editTaskEndDate"),
  editRepeatUnit: document.querySelector("#editRepeatUnit"),
  editN: document.querySelector("#editN"),
  cancelTaskEditBtn: document.querySelector("#cancelTaskEditBtn"),
  oneTimeForm: document.querySelector("#oneTimeForm"),
  recurringForm: document.querySelector("#recurringForm"),
  statusFilter: document.querySelector("#statusFilter"),
  fromDateFilter: document.querySelector("#fromDateFilter"),
  toDateFilter: document.querySelector("#toDateFilter"),
  searchFilter: document.querySelector("#searchFilter"),
  selectVisibleBtn: document.querySelector("#selectVisibleBtn"),
  clearSelectedBtn: document.querySelector("#clearSelectedBtn"),
  markSelectedDoneBtn: document.querySelector("#markSelectedDoneBtn"),
  selectAllToggle: document.querySelector("#selectAllToggle"),
  selectedCount: document.querySelector("#selectedCount"),
  toast: document.querySelector("#toast"),
};

function scheduleKey(item) {
  return `${item.task_id}#${item.schedule_id}`;
}

function toast(message, tone = "ok") {
  refs.toast.textContent = message;
  refs.toast.className = "toast show";
  if (tone !== "ok") refs.toast.classList.add(tone);
  setTimeout(() => {
    refs.toast.className = "toast";
  }, 1800);
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : {},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Request failed.");
  return body;
}

function setBusy(value) {
  state.busy = value;
  refs.markSelectedDoneBtn.disabled = value;
}

function filteredSchedules() {
  const statusMode = refs.statusFilter.value;
  const fromDate = refs.fromDateFilter.value;
  const toDate = refs.toDateFilter.value;
  const keyword = refs.searchFilter.value.trim().toLowerCase();

  return state.schedules.filter((item) => {
    if (statusMode === "todo" && item.status !== "todo") return false;
    if (statusMode === "active" && !["todo", "doing"].includes(item.status)) return false;
    if (fromDate && item.end_date < fromDate) return false;
    if (toDate && item.start_date > toDate) return false;
    if (!keyword) return true;
    return (
      item.name.toLowerCase().includes(keyword) ||
      item.task_id.toLowerCase().includes(keyword)
    );
  });
}

function updateSelectionSummary() {
  refs.selectedCount.textContent = `已选 ${state.selectedKeys.size} 项`;
  if (!state.visibleSchedules.length) {
    refs.selectAllToggle.checked = false;
    refs.selectAllToggle.indeterminate = false;
    return;
  }
  const visibleKeys = state.visibleSchedules.map(scheduleKey);
  const checkedCount = visibleKeys.filter((key) => state.selectedKeys.has(key)).length;
  refs.selectAllToggle.checked = checkedCount > 0 && checkedCount === visibleKeys.length;
  refs.selectAllToggle.indeterminate = checkedCount > 0 && checkedCount < visibleKeys.length;
}

function renderStatusEditor(item, prefix) {
  const key = `${prefix}-${scheduleKey(item)}`;
  return `
    <div class="status-editor">
      <select data-status-key="${key}" data-task="${item.task_id}" data-sid="${item.schedule_id}">
        <option value="todo" ${item.status === "todo" ? "selected" : ""}>todo</option>
        <option value="doing" ${item.status === "doing" ? "selected" : ""}>doing</option>
        <option value="done" ${item.status === "done" ? "selected" : ""}>done</option>
      </select>
      <button class="mini-btn" data-save-status="${key}">保存</button>
      <button class="mini-btn" data-mark-done="${item.task_id}" data-sid="${item.schedule_id}" ${item.status === "done" ? "disabled" : ""}>Done</button>
    </div>
  `;
}

function renderSchedules() {
  state.visibleSchedules = filteredSchedules();
  refs.scheduleBody.innerHTML = "";
  for (const item of state.visibleSchedules) {
    const key = scheduleKey(item);
    const checked = state.selectedKeys.has(key) ? "checked" : "";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-row-check="${key}" ${checked} /></td>
      <td class="task-id">${item.task_id}#${item.schedule_id}</td>
      <td>${item.name}</td>
      <td>${item.start_date} -> ${item.end_date}</td>
      <td><span class="status-pill status-${item.status}">${item.status}</span></td>
      <td>${renderStatusEditor(item, "main")}</td>
    `;
    refs.scheduleBody.append(tr);
  }
  updateSelectionSummary();
}

function renderOverdue() {
  refs.overdueBody.innerHTML = "";
  if (!state.overdueSchedules.length) {
    refs.overdueEmpty.classList.remove("hidden");
    return;
  }
  refs.overdueEmpty.classList.add("hidden");
  for (const item of state.overdueSchedules) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="task-id">${item.task_id}#${item.schedule_id}</td>
      <td>${item.name}</td>
      <td>${item.start_date} -> ${item.end_date}</td>
      <td><span class="status-pill status-${item.status}">${item.status}</span></td>
      <td>${renderStatusEditor(item, "overdue")}</td>
    `;
    refs.overdueBody.append(tr);
  }
}

function renderTasks() {
  refs.taskBody.innerHTML = "";
  for (const task of state.tasks) {
    const isRecurring = task.kind === "recurring";
    const windowText = isRecurring
      ? `${task.task_start_date} -> ${task.task_end_date}`
      : `${task.start_date} -> ${task.end_date}`;
    const repeatText = isRecurring ? `${task.n} ${task.repeat_unit}` : "-";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="task-id">${task.task_id}</td>
      <td>${task.kind}</td>
      <td>${task.name}</td>
      <td>${windowText}</td>
      <td>${repeatText}</td>
      <td><button class="mini-btn" data-edit-task="${task.task_id}">编辑</button></td>
    `;
    refs.taskBody.append(tr);
  }
}

function openTaskEditor(taskId) {
  const task = state.tasks.find((item) => item.task_id === taskId);
  if (!task) {
    toast("任务不存在", "error");
    return;
  }
  const isRecurring = task.kind === "recurring";
  refs.taskEditForm.classList.remove("hidden");
  refs.taskEditTitle.textContent = `编辑任务 ${task.task_id}`;
  refs.editTaskId.value = task.task_id;
  refs.editTaskKind.value = task.kind;
  refs.editName.value = task.name || "";
  refs.editDescription.value = task.description || "";
  refs.editOneTimeFields.classList.toggle("hidden", isRecurring);
  refs.editRecurringFields.classList.toggle("hidden", !isRecurring);

  if (isRecurring) {
    refs.editFirstStartDate.value = task.first_start_date || "";
    refs.editFirstEndDate.value = task.first_end_date || "";
    refs.editTaskStartDate.value = task.task_start_date || "";
    refs.editTaskEndDate.value = task.task_end_date || "";
    refs.editRepeatUnit.value = task.repeat_unit || "day";
    refs.editN.value = task.n || 1;
  } else {
    refs.editStartDate.value = task.start_date || "";
    refs.editEndDate.value = task.end_date || "";
  }
}

function closeTaskEditor() {
  refs.taskEditForm.classList.add("hidden");
  refs.taskEditTitle.textContent = "编辑任务";
  refs.taskEditForm.reset();
}

function initFilters(today) {
  refs.statusFilter.value = "todo";
  refs.fromDateFilter.value = today;
  refs.toDateFilter.value = today;
  state.initializedFilters = true;
}

async function refresh() {
  const data = await api("/api/overview");
  refs.todayValue.textContent = data.today;
  refs.taskCount.textContent = data.counts.tasks;
  refs.scheduleCount.textContent = data.counts.schedules;
  refs.overdueCount.textContent = data.counts.overdue;
  state.schedules = data.schedules;
  state.overdueSchedules = data.overdue;
  state.tasks = data.tasks;

  if (!state.initializedFilters) initFilters(data.today);
  renderSchedules();
  renderOverdue();
  renderTasks();
}

async function setScheduleStatus(taskId, sid, status) {
  await api("/api/schedules/status", {
    task_id: taskId,
    schedule_id: sid,
    status,
  });
}

async function markSelectedDone() {
  if (!state.selectedKeys.size) {
    toast("请先选择要完成的日程", "warn");
    return;
  }
  setBusy(true);
  try {
    const keyToItem = new Map(state.schedules.map((item) => [scheduleKey(item), item]));
    const targets = [...state.selectedKeys]
      .map((key) => keyToItem.get(key))
      .filter((item) => item && item.status !== "done");
    await Promise.all(targets.map((item) => setScheduleStatus(item.task_id, item.schedule_id, "done")));
    state.selectedKeys.clear();
    await refresh();
    toast(`已更新 ${targets.length} 项为 done`);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function payloadFromForm(form) {
  const fd = new FormData(form);
  const obj = Object.fromEntries(fd.entries());
  for (const [k, v] of Object.entries(obj)) {
    if (v === "") obj[k] = null;
  }
  obj.is_test = fd.get("is_test") === "on";
  if ("n" in obj && obj.n !== null) obj.n = Number(obj.n);
  return obj;
}

refs.oneTimeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/tasks/one-time", payloadFromForm(refs.oneTimeForm));
    refs.oneTimeForm.reset();
    await refresh();
    toast("一次性任务已创建");
  } catch (error) {
    toast(error.message, "error");
  }
});

refs.recurringForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/tasks/recurring", payloadFromForm(refs.recurringForm));
    refs.recurringForm.reset();
    await refresh();
    toast("周期任务已创建");
  } catch (error) {
    toast(error.message, "error");
  }
});

refs.taskEditForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const taskId = refs.editTaskId.value;
  const kind = refs.editTaskKind.value;
  setBusy(true);
  try {
    if (kind === "one_time") {
      await api("/api/tasks/one-time/update", {
        task_id: taskId,
        name: refs.editName.value,
        description: refs.editDescription.value,
        start_date: refs.editStartDate.value,
        end_date: refs.editEndDate.value,
      });
    } else {
      await api("/api/tasks/recurring/update", {
        task_id: taskId,
        name: refs.editName.value,
        description: refs.editDescription.value,
        first_start_date: refs.editFirstStartDate.value,
        first_end_date: refs.editFirstEndDate.value,
        task_start_date: refs.editTaskStartDate.value,
        task_end_date: refs.editTaskEndDate.value,
        repeat_unit: refs.editRepeatUnit.value,
        n: Number(refs.editN.value || 1),
      });
    }
    closeTaskEditor();
    await refresh();
    toast("任务已更新");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
});

refs.cancelTaskEditBtn.addEventListener("click", () => {
  closeTaskEditor();
});

document.body.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  const editTaskId = button.dataset.editTask;
  if (editTaskId) {
    openTaskEditor(editTaskId);
    return;
  }

  const action = button.dataset.action;
  if (action) {
    try {
      if (action === "maintenance") await api("/api/maintenance", {});
      if (action === "done-overdue") await api("/api/schedules/done-overdue", {});
      if (action === "delay-overdue") await api("/api/tasks/delay-overdue", {});
      await refresh();
      toast("操作成功");
    } catch (error) {
      toast(error.message, "warn");
    }
    return;
  }

  if (button.id === "selectVisibleBtn") {
    for (const item of state.visibleSchedules) state.selectedKeys.add(scheduleKey(item));
    renderSchedules();
    return;
  }

  if (button.id === "clearSelectedBtn") {
    state.selectedKeys.clear();
    renderSchedules();
    return;
  }

  if (button.id === "markSelectedDoneBtn") {
    await markSelectedDone();
    return;
  }

  const saveStatusKey = button.dataset.saveStatus;
  if (saveStatusKey) {
    const select = document.querySelector(`select[data-status-key="${saveStatusKey}"]`);
    if (!select) return;
    const taskId = select.dataset.task;
    const sid = Number(select.dataset.sid);
    const status = select.value;
    setBusy(true);
    try {
      await setScheduleStatus(taskId, sid, status);
      state.selectedKeys.delete(`${taskId}#${sid}`);
      await refresh();
      toast(`状态已更新为 ${status}`);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(false);
    }
    return;
  }

  const markDoneTask = button.dataset.markDone;
  if (markDoneTask) {
    const sid = Number(button.dataset.sid);
    setBusy(true);
    try {
      await setScheduleStatus(markDoneTask, sid, "done");
      state.selectedKeys.delete(`${markDoneTask}#${sid}`);
      await refresh();
      toast("已标记为 done");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }
});

document.body.addEventListener("change", (event) => {
  const checkbox = event.target.closest("input[type='checkbox'][data-row-check]");
  if (!checkbox) return;
  const key = checkbox.dataset.rowCheck;
  if (!key) return;
  if (checkbox.checked) state.selectedKeys.add(key);
  else state.selectedKeys.delete(key);
  updateSelectionSummary();
});

refs.selectAllToggle.addEventListener("change", () => {
  if (refs.selectAllToggle.checked) {
    for (const item of state.visibleSchedules) state.selectedKeys.add(scheduleKey(item));
  } else {
    for (const item of state.visibleSchedules) state.selectedKeys.delete(scheduleKey(item));
  }
  renderSchedules();
});

refs.statusFilter.addEventListener("change", renderSchedules);
refs.fromDateFilter.addEventListener("change", renderSchedules);
refs.toDateFilter.addEventListener("change", renderSchedules);
refs.searchFilter.addEventListener("input", renderSchedules);

refresh().catch((error) => toast(error.message, "error"));
