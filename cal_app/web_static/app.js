const state = {
  schedules: [],
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
  searchFilter: document.querySelector("#searchFilter"),
  toast: document.querySelector("#toast"),
};

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

function renderSchedules() {
  const status = refs.statusFilter.value;
  const keyword = refs.searchFilter.value.trim().toLowerCase();
  const filtered = state.schedules.filter((item) => {
    if (status && item.status !== status) return false;
    if (!keyword) return true;
    return (
      item.name.toLowerCase().includes(keyword) ||
      item.task_id.toLowerCase().includes(keyword)
    );
  });

  refs.scheduleBody.innerHTML = "";
  for (const item of filtered) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="task-id">${item.task_id}#${item.schedule_id}</td>
      <td>${item.name}</td>
      <td>${item.start_date} -> ${item.end_date}</td>
      <td>
        <span class="status-pill status-${item.status}">${item.status}</span>
      </td>
      <td>
        <select data-task="${item.task_id}" data-sid="${item.schedule_id}">
          <option value="todo" ${item.status === "todo" ? "selected" : ""}>todo</option>
          <option value="doing" ${item.status === "doing" ? "selected" : ""}>doing</option>
          <option value="done" ${item.status === "done" ? "selected" : ""}>done</option>
        </select>
        <button class="mini-btn" data-save="${item.task_id}" data-sid="${item.schedule_id}">
          保存
        </button>
      </td>
    `;
    refs.scheduleBody.append(tr);
  }
}

async function refresh() {
  const data = await api("/api/overview");
  refs.todayValue.textContent = data.today;
  refs.taskCount.textContent = data.counts.tasks;
  refs.scheduleCount.textContent = data.counts.schedules;
  refs.overdueCount.textContent = data.counts.overdue;
  state.schedules = data.schedules;
  renderSchedules();
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
    const payload = payloadFromForm(refs.oneTimeForm);
    await api("/api/tasks/one-time", payload);
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
    const payload = payloadFromForm(refs.recurringForm);
    await api("/api/tasks/recurring", payload);
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

  const saveTask = button.dataset.save;
  if (!saveTask) return;

  const sid = Number(button.dataset.sid);
  const select = document.querySelector(`select[data-task="${saveTask}"][data-sid="${sid}"]`);
  if (!select) return;

  try {
    await api("/api/schedules/status", {
      task_id: saveTask,
      schedule_id: sid,
      status: select.value,
    });
    await refresh();
    toast("状态已更新");
  } catch (error) {
    toast(error.message, "error");
  }
});

refs.statusFilter.addEventListener("change", renderSchedules);
refs.searchFilter.addEventListener("input", renderSchedules);

refresh().catch((error) => toast(error.message, "error"));
