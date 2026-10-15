<div class="row g-4">
    <div class="col-md-4">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <h4 class="fw-bold mb-1"><?= htmlspecialchars($contact['first_name'] . ' ' . $contact['last_name']) ?></h4>
                <p class="text-muted small"><?= htmlspecialchars($contact['position'] ?? 'No Position Defined') ?></p>

                <hr>

                <div class="mb-2">
                    <strong>Email:</strong> <?= htmlspecialchars($contact['email'] ?? 'N/A') ?>
                </div>
                <div class="mb-2">
                    <strong>Phone:</strong> <?= htmlspecialchars($contact['phone'] ?? 'N/A') ?>
                </div>
                <div class="mb-2">
                    <strong>Company:</strong> <?= htmlspecialchars($contact['company_name'] ?? 'N/A') ?>
                </div>
                <div class="mb-2">
                    <strong>Account Owner:</strong> <?= htmlspecialchars($contact['assigned_user'] ?? 'Unassigned') ?>
                </div>
                <div class="mb-2">
                    <strong>Status:</strong> <span class="badge bg-primary"><?= htmlspecialchars(strtoupper($contact['status'])) ?></span>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card border-0 shadow-sm mb-4">
            <div class="card-header bg-white fw-bold">Add Note Log</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=contacts/add-note">
                    <?= \Core\Csrf::field() ?>
                    <input type="hidden" name="contact_id" value="<?= $contact['id'] ?>">
                    <div class="mb-3">
                        <textarea name="content" class="form-control" rows="3" placeholder="Log discussion details or updates..." required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary btn-sm">Add Note</button>
                </form>
            </div>
        </div>

        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Activity Timeline</div>
            <div class="card-body">
                <?php if (empty($notes)): ?>
                    <p class="text-muted mb-0 small">No notes logged yet.</p>
                <?php else: ?>
                    <div class="timeline">
                        <?php foreach ($notes as $note): ?>
                            <div class="border-bottom pb-2 mb-3">
                                <div class="d-flex justify-content-between">
                                    <span class="fw-bold small"><?= htmlspecialchars($note['author_name']) ?></span>
                                    <span class="text-muted small"><?= htmlspecialchars($note['created_at']) ?></span>
                                </div>
                                <p class="mb-0 text-secondary mt-1"><?= nl2br(htmlspecialchars($note['content'])) ?></p>
                            </div>
                        <?php endforeach; ?>
                    </div>
                <?php endif; ?>
            </div>
        </div>
    </div>
</div>