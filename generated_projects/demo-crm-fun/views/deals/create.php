<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">New Deal</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=deals/store">
                    <?= \Core\Csrf::field() ?>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Deal Title *</label>
                            <input type="text" name="title" class="form-control" required placeholder="e.g. Enterprise Software License">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Deal Value ($) *</label>
                            <input type="number" step="0.01" name="amount" class="form-control" required placeholder="0.00">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Pipeline Stage</label>
                            <select name="stage" class="form-select">
                                <?php foreach ($deal_stages as $key => $label): ?>
                                    <option value="<?= $key ?>"><?= htmlspecialchars($label) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Expected Close Date</label>
                            <input type="date" name="expected_close_date" class="form-control">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Primary Contact</label>
                            <select name="contact_id" class="form-select">
                                <option value="">-- Select Contact --</option>
                                <?php foreach ($contacts as $c): ?>
                                    <option value="<?= $c['id'] ?>"><?= htmlspecialchars($c['first_name'] . ' ' . $c['last_name']) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Associated Company</label>
                            <select name="company_id" class="form-select">
                                <option value="">-- Select Company --</option>
                                <?php foreach ($companies as $comp): ?>
                                    <option value="<?= $comp['id'] ?>"><?= htmlspecialchars($comp['name']) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary">Create Deal</button>
                        <a href="index.php?route=deals" class="btn btn-light">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>