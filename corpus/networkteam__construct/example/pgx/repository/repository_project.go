package repository

import (
	"context"

	"github.com/gofrs/uuid"
	. "github.com/networkteam/qrb"
	"github.com/networkteam/qrb/builder"
	"github.com/networkteam/qrb/fn"
	"github.com/networkteam/qrb/qrbpgx"

	"github.com/networkteam/construct/v2/constructpgx"
	"github.com/networkteam/construct/v2/example/pgx/model"
)

type ProjectQueryOpts struct {
	IncludeTodoCount bool
}

// projectBuildFindQuery creates a partial builder.SelectBuilder that
// - selects a single JSON result by using projectJson (which selects a TodoCount if opts.IncludeTodoCount is true)
// - from the projects table
func projectBuildFindQuery(opts ProjectQueryOpts) builder.SelectBuilder {
	return SelectJson(projectJson(opts)).
		From(project).
		SelectBuilder
}

// FindProjectByID finds a single project by id
func FindProjectByID(ctx context.Context, executor qrbpgx.Executor, id uuid.UUID, opts ProjectQueryOpts) (result model.Project, err error) {
	q := projectBuildFindQuery(opts).
		Where(project.ID.Eq(Arg(id)))

	return constructpgx.ScanRow[model.Project](
		qrbpgx.Build(q).WithExecutor(executor).QueryRow(ctx),
	)
}

// FindAllProjects finds all projects sorted by title
func FindAllProjects(ctx context.Context, executor qrbpgx.Executor, opts ProjectQueryOpts) (result []model.Project, err error) {
	q := projectBuildFindQuery(opts).
		OrderBy(project.Title)

	return constructpgx.CollectRows[model.Project](
		qrbpgx.Build(q).WithExecutor(executor).Query(ctx),
	)
}

// InsertProject inserts a new project from a ProjectChangeSet
func InsertProject(ctx context.Context, executor qrbpgx.Executor, changeSet ProjectChangeSet) error {
	q := InsertInto(project).
		SetMap(changeSet.toMap())

	_, err := qrbpgx.Build(q).WithExecutor(executor).Exec(ctx)
	return err
}

func projectJson(opts ProjectQueryOpts) builder.JsonBuildObjectBuilder {
	// Use the generated default select (JSON object builder) and add another property for the aggregated count#
	// (if opts.IncludeTodoCount is true).
	return projectDefaultJson.
		PropIf(
			opts.IncludeTodoCount,
			"TodoCount",
			Select(fn.Count(N("*"))).
				From(todo).
				Where(todo.ProjectID.Eq(project.ID)),
		)
}
