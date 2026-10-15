<div class="row g-4">
    <div class="col-md-4">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">New Follow-up Task</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=tasks/store">
                    <?= \Core\Csrf::field() ?>
                    <div class="mb-3">
                        <label class="form-label">Task Title *</label>
                        <input type="text" name="title" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Due Date *</label>
                        <input type="date" name="due_date" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Priority Level</label>
                        <select name="priority" class="form-select">
                            <option value="Low">Low</option>
                            <option value="Medium" selected>Medium</option>
                            <option value="High">High</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Assigned Agent</label>
                        <select name="assigned_to" class="form-select">
                            <?php foreach ($users as $usr): ?>
                                <option value="<?= $usr['id'] ?>"><?= htmlspecialchars($usr['name']) ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="2"></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Create Task</button>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Tasks List</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Task</th>
                                <th>Due</th>
                                <th>Priority</th>
                                <th>Status</th>
                                <th>Assigned</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($tasks as $task): ?>
                            <tr>
                                <td>
                                    <div class="fw-bold"><?= htmlspecialchars($task['title']) ?></div>
                                    <small class="text-muted"><?= htmlspecialchars($task['description'] ?? '') ?></small>
                                </td>
                                <td><?= htmlspecialchars($task['due_date']) ?></td>
                                <td>
                                    <span class="badge bg-<?= $task['priority'] === 'High' ? 'danger' : ($task['priority'] === 'Medium' ? 'warning text-dark' : 'secondary') ?>">
                                        <?= htmlspecialchars($task['priority']) ?>
                                    </span>
                                </td>
                                <td>
                                    <form method="POST" action="index.php?route=tasks/update-status" class="d-inline">
                                        <?= \Core\Csrf::field() ?>
                                        <input type="hidden" name="id" value="<?= $task['id'] ?>">
                                        <select name="status" class="form-select form-select-sm" onchange="this.form.submit()">
                                            <option value="Pending" <?= $task['status'] === 'Pending' ? 'selected' : '' ?>>Pending</option>
                                            <option value="In Progress" <?= $task['status'] === 'In Progress' ? 'selected' : '' ?>>In Progress</option>
                                            <option value="Completed" <?= $task['status'] === 'Completed' ? 'selected' : '' ?>>Completed</option>
                                        </select>
                                    </form>
                                </td>
                                <td><?= htmlspecialchars($task['assigned_name'] ?? 'Unassigned') ?></td>
                                <td class="text-end">
                                    <?php if (\Core\Auth::hasRole(['admin', 'manager'])): ?>
                                    <form method="POST" action="index.php?route=tasks/delete" class="d-inline" onsubmit="return confirm('Delete task?');">
                                        <?= \Core\Csrf::field() ?>
                                        <input type="hidden" name="id" value="<?= $task['id'] ?>">
                                        <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
                                    </form>
                                    <?php endif; ?>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>