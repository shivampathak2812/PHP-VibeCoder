<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Edit Contact</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=contacts/update">
                    <?= \Core\Csrf::field() ?>
                    <input type="hidden" name="id" value="<?= $contact['id'] ?>">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">First Name *</label>
                            <input type="text" name="first_name" class="form-control" value="<?= htmlspecialchars($contact['first_name']) ?>" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Last Name *</label>
                            <input type="text" name="last_name" class="form-control" value="<?= htmlspecialchars($contact['last_name']) ?>" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Email</label>
                            <input type="email" name="email" class="form-control" value="<?= htmlspecialchars($contact['email'] ?? '') ?>">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Phone</label>
                            <input type="text" name="phone" class="form-control" value="<?= htmlspecialchars($contact['phone'] ?? '') ?>">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Job Position</label>
                            <input type="text" name="position" class="form-control" value="<?= htmlspecialchars($contact['position'] ?? '') ?>">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Company</label>
                            <select name="company_id" class="form-select">
                                <option value="">-- Select Company --</option>
                                <?php foreach ($companies as $comp): ?>
                                    <option value="<?= $comp['id'] ?>" <?= $comp['id'] == $contact['company_id'] ? 'selected' : '' ?>>
                                        <?= htmlspecialchars($comp['name']) ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Assigned Owner</label>
                            <select name="assigned_to" class="form-select">
                                <option value="">-- Assign User --</option>
                                <?php foreach ($users as $usr): ?>
                                    <option value="<?= $usr['id'] ?>" <?= $usr['id'] == $contact['assigned_to'] ? 'selected' : '' ?>>
                                        <?= htmlspecialchars($usr['name']) ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Status</label>
                            <select name="status" class="form-select">
                                <option value="lead" <?= $contact['status'] === 'lead' ? 'selected' : '' ?>>Lead</option>
                                <option value="customer" <?= $contact['status'] === 'customer' ? 'selected' : '' ?>>Customer</option>
                                <option value="inactive" <?= $contact['status'] === 'inactive' ? 'selected' : '' ?>>Inactive</option>
                            </select>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary">Update Contact</button>
                        <a href="index.php?route=contacts" class="btn btn-light">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>