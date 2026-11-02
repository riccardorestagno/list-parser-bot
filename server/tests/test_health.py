def test_health_names_the_release(client):
    response = client.get("/health")
    assert response.status_code == 200
    # No version.txt in a clone: deploy.yml writes it into the package
    assert response.json() == {"status": "ok", "version": "dev"}
