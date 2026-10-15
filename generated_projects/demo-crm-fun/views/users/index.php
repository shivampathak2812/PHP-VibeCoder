<div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="fw-bold">User Management</h3>
    <a href="index.php?route=users/create" class="btn btn-primary"><i class="bi bi-person-plus"></i> Add User Account</a>
</div>

<div class="card border-0 shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Created At</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($users as $u): ?>
                    <tr>
                        <td><?= $u['id'] ?></td>
                        <td class="fw-bold"><?= htmlspecialchars($u['name']) ?></td>
                        <td><?= htmlspecialchars($u['email']) ?></td>
                        <td><span class="badge bg-dark"><?= htmlspecialchars(strtoupper($u['role'])) ?></span></td>
                        <td><?= htmlspecialchars($u['created_at']) ?></td>
                        <td class="text-end">
                            <?php if ($u['id'] !== \Core\Auth::id()): ?>
                            <form method="POST" action="index.php?route=users/delete" class="d-inline" onsubmit="return confirm('Revoke account?');">
                                <?= \Core\Csrf::field() ?>
                                <input type="hidden" name="id" value="<?= $u['id'] ?>">
                                <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i> Delete</button>
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