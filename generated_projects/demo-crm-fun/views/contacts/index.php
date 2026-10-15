<div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="fw-bold">Contact Directory</h3>
    <a href="index.php?route=contacts/create" class="btn btn-primary"><i class="bi bi-plus-lg"></i> Add Contact</a>
</div>

<div class="card border-0 shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Company</th>
                        <th>Assigned To</th>
                        <th>Status</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($contacts as $contact): ?>
                    <tr>
                        <td>
                            <a href="index.php?route=contacts/show&id=<?= $contact['id'] ?>" class="fw-bold text-decoration-none">
                                <?= htmlspecialchars($contact['first_name'] . ' ' . $contact['last_name']) ?>
                            </a>
                            <br><small class="text-muted"><?= htmlspecialchars($contact['position'] ?? '') ?></small>
                        </td>
                        <td><?= htmlspecialchars($contact['email'] ?? '-') ?></td>
                        <td><?= htmlspecialchars($contact['phone'] ?? '-') ?></td>
                        <td><?= htmlspecialchars($contact['company_name'] ?? 'N/A') ?></td>
                        <td><?= htmlspecialchars($contact['assigned_user'] ?? 'Unassigned') ?></td>
                        <td><span class="badge bg-info text-dark"><?= htmlspecialchars(strtoupper($contact['status'])) ?></span></td>
                        <td class="text-end">
                            <a href="index.php?route=contacts/edit&id=<?= $contact['id'] ?>" class="btn btn-sm btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                            <?php if (\Core\Auth::hasRole(['admin', 'manager'])): ?>
                            <form method="POST" action="index.php?route=contacts/delete" class="d-inline" onsubmit="return confirm('Delete this contact?');">
                                <?= \Core\Csrf::field() ?>
                                <input type="hidden" name="id" value="<?= $contact['id'] ?>">
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