# Modules API

Study modules are top-level containers (e.g. "Linear Algebra") that hold documents.

## Endpoints

### `GET /api/modules/`
Returns all study modules.

### `POST /api/modules/`
Create a new module.

**Request body:**

    {
      "name": "Linear Algebra",
      "description": "Math semester 2",
      "color": "#4a90d9"
    }

### `GET /api/modules/{id}`
Returns a single module by ID.

### `PUT /api/modules/{id}`
Update a module.

### `DELETE /api/modules/{id}`
Delete a module and all associated documents (cascade).

## Source Code
```{eval-rst}
.. automodule:: backend.api.modules
   :members:
```