const state = {
  schedules: [],
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
  if (!response.ok) {
    throw new Error(body.error || "Request failed.");
  }
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

function renderSchedules() {
  state.visibleSchedules = filteredSchedules();
  refs.scheduleBody.innerHTML = "";

  for (const item of state.visibleSchedules) {
    const key = scheduleKey(item);
    const checked = state.selectedKeys.has(key) ? "checked" : "";
    const doneDisabled = item.status === "done" ? "disabled" : "";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-row-check="${key}" ${checked} /></td>
      <td class="task-id">${item.task_id}#${item.schedule_id}</td>
      <td>${item.name}</td>
      <td>${item.start_date} -> ${item.end_date}</td>
      <td><span class="status-pill status-${item.status}">${item.status}</span></td>
      <td>
        <button class="mini-btn" data-mark-done="${item.task_id}" data-sid="${item.schedule_id}" ${doneDisabled}>
          Done
        </button>
      </td>
    `;
    refs.scheduleBody.append(tr);
  }
  updateSelectionSummary();
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

  if (!state.initializedFilters) initFilters(data.today);
  renderSchedules();
}

async function setScheduleDone(taskId, sid) {
  await api("/api/schedules/status", {
    task_id: taskId,
    schedule_id: sid,
    status: "done",
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
    await Promise.all(
      targets.map((item) => setScheduleDone(item.task_id, item.schedule_id)),
    );
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

document.body.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

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

  const markDoneTask = button.dataset.markDone;
  if (markDoneTask) {
    const sid = Number(button.dataset.sid);
    setBusy(true);
    try {
      await setScheduleDone(markDoneTask, sid);
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
