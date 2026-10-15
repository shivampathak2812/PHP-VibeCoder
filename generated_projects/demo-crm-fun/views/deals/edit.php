<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Update Deal</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=deals/update">
                    <?= \Core\Csrf::field() ?>
                    <input type="hidden" name="id" value="<?= $deal['id'] ?>">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Deal Title *</label>
                            <input type="text" name="title" class="form-control" value="<?= htmlspecialchars($deal['title']) ?>" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Deal Value ($) *</label>
                            <input type="number" step="0.01" name="amount" class="form-control" value="<?= htmlspecialchars((string)$deal['amount']) ?>" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Pipeline Stage</label>
                            <select name="stage" class="form-select">
                                <?php foreach ($deal_stages as $key => $label): ?>
                                    <option value="<?= $key ?>" <?= $deal['stage'] === $key ? 'selected' : '' ?>><?= htmlspecialchars($label) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Expected Close Date</label>
                            <input type="date" name="expected_close_date" class="form-control" value="<?= htmlspecialchars($deal['expected_close_date'] ?? '') ?>">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Primary Contact</label>
                            <select name="contact_id" class="form-select">
                                <option value="">-- Select Contact --</option>
                                <?php foreach ($contacts as $c): ?>
                                    <option value="<?= $c['id'] ?>" <?= $c['id'] == $deal['contact_id'] ? 'selected' : '' ?>>
                                        <?= htmlspecialchars($c['first_name'] . ' ' . $c['last_name']) ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Associated Company</label>
                            <select name="company_id" class="form-select">
                                <option value="">-- Select Company --</option>
                                <?php foreach ($companies as $comp): ?>
                                    <option value="<?= $comp['id'] ?>" <?= $comp['id'] == $deal['company_id'] ? 'selected' : '' ?>>
                                        <?= htmlspecialchars($comp['name']) ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary">Update Deal</button>
                        <a href="index.php?route=deals" class="btn btn-light">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>