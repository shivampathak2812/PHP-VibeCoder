<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Edit Company</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=companies/update">
                    <?= \Core\Csrf::field() ?>
                    <input type="hidden" name="id" value="<?= $company['id'] ?>">
                    <div class="mb-3">
                        <label class="form-label">Company Name *</label>
                        <input type="text" name="name" class="form-control" value="<?= htmlspecialchars($company['name']) ?>" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Industry</label>
                        <input type="text" name="industry" class="form-control" value="<?= htmlspecialchars($company['industry'] ?? '') ?>">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Phone</label>
                        <input type="text" name="phone" class="form-control" value="<?= htmlspecialchars($company['phone'] ?? '') ?>">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" value="<?= htmlspecialchars($company['email'] ?? '') ?>">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Website</label>
                        <input type="url" name="website" class="form-control" value="<?= htmlspecialchars($company['website'] ?? '') ?>">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Address</label>
                        <textarea name="address" class="form-control" rows="2"><?= htmlspecialchars($company['address'] ?? '') ?></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Update</button>
                    <a href="index.php?route=companies" class="btn btn-light">Cancel</a>
                </form>
            </div>
        </div>
    </div>
</div>