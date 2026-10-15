<div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="fw-bold">Pipeline Deals</h3>
    <a href="index.php?route=deals/create" class="btn btn-primary"><i class="bi bi-plus-lg"></i> Create Deal</a>
</div>

<div class="card border-0 shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Deal Title</th>
                        <th>Amount</th>
                        <th>Stage</th>
                        <th>Contact / Company</th>
                        <th>Expected Close</th>
                        <th>Owner</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($deals as $deal): ?>
                    <tr>
                        <td class="fw-bold"><?= htmlspecialchars($deal['title']) ?></td>
                        <td class="text-success fw-bold">$<?= number_format((float)$deal['amount'], 2) ?></td>
                        <td>
                            <span class="badge bg-secondary"><?= htmlspecialchars($deal_stages[$deal['stage']] ?? $deal['stage']) ?></span>
                        </td>
                        <td>
                            <?= htmlspecialchars($deal['contact_name'] ?? 'N/A') ?> 
                            <small class="text-muted d-block"><?= htmlspecialchars($deal['company_name'] ?? '') ?></small>
                        </td>
                        <td><?= htmlspecialchars($deal['expected_close_date'] ?? 'TBD') ?></td>
                        <td><?= htmlspecialchars($deal['owner_name'] ?? 'System') ?></td>
                        <td class="text-end">
                            <a href="index.php?route=deals/edit&id=<?= $deal['id'] ?>" class="btn btn-sm btn-outline-secondary"><i class="bi bi-pencil"></i></a>
                            <?php if (\Core\Auth::hasRole(['admin', 'manager'])): ?>
                            <form method="POST" action="index.php?route=deals/delete" class="d-inline" onsubmit="return confirm('Delete deal?');">
                                <?= \Core\Csrf::field() ?>
                                <input type="hidden" name="id" value="<?= $deal['id'] ?>">
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