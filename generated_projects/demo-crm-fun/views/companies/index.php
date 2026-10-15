<div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="fw-bold">Companies</h3>
    <a href="index.php?route=companies/create" class="btn btn-primary"><i class="bi bi-plus-lg"></i> Add Company</a>
</div>

<div class="card border-0 shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Company Name</th>
                        <th>Industry</th>
                        <th>Phone</th>
                        <th>Website</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($companies as $comp): ?>
                    <tr>
                        <td class="fw-bold"><?= htmlspecialchars($comp['name']) ?></td>
                        <td><?= htmlspecialchars($comp['industry'] ?? '-') ?></td>
                        <td><?= htmlspecialchars($comp['phone'] ?? '-') ?></td>
                        <td>
                            <?php if (!empty($comp['website'])): ?>
                                <a href="<?= htmlspecialchars($comp['website']) ?>" target="_blank"><?= htmlspecialchars($comp['website']) ?></a>
                            <?php else: ?>
                                -
                            <?php endif; ?>
                        </td>
                        <td class="text-end">
                            <a href="index.php?route=companies/edit&id=<?= $comp['id'] ?>" class="btn btn-sm btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                            <?php if (\Core\Auth::hasRole(['admin', 'manager'])): ?>
                            <form method="POST" action="index.php?route=companies/delete" class="d-inline" onsubmit="return confirm('Delete company?');">
                                <?= \Core\Csrf::field() ?>
                                <input type="hidden" name="id" value="<?= $comp['id'] ?>">
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