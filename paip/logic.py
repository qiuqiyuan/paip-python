## Idea 1: Uniform database

class Database(object):
    """A store for clauses and primitives."""

    # We store all of the clauses--rules and facts--in one database, indexed
    # by the predicates of their head relations.  This makes it quicker and
    # easier to search through possibly applicable rules and facts when we
    # encounter a goal relation.

    # We can also store "primitives", or procedures, in the database.
    
    def __init__(self, facts=None, rules=None):
        facts = facts or []
        rules = rules or []
        self.clauses = {}
        for clause in facts + rules:
            self.store(clause)

    def store(self, clause):
        # Add each clause in the database to the list of clauses indexed
        # on the head's predicate.
        self.clauses.setdefault(clause.head.pred, []).append(clause)

    def define_primitive(self, name, fn):
        self.clauses[name] = fn

    def query(self, pred):
        # Retrieve clauses by their head's predicate.
        return self.clauses[pred]

    def __str__(self):
        clauses = []
        for cl in self.clauses.values():
            clauses.extend(cl)
        return '\n'.join(map(str, clauses))


## Idea 2: Unification of logic variables

class Atom(object):
    """Represents any literal (symbol, number, string)."""
    
    def __init__(self, atom):
        self.atom = atom
        
    def __str__(self):
        return str(self.atom)

    def __repr__(self):
        return 'Atom(%s)' % repr(self.atom)

    def __eq__(self, other):
        return isinstance(other, Atom) and other.atom == self.atom

    def unify(self, other, bindings):
        if isinstance(other, Atom):
            return dict(bindings) if self.atom == other.atom else False

        if isinstance(other, Var):
            bindings = dict(bindings)

            # Find the Atom that other is bound to, if one exists
            binding = other.lookup(bindings)

            # If other is already bound to an Atom, make sure it matches self.
            if binding and binding != self:
                return False
            if binding and binding == self:
                return bindings
            
            # Otherwise bind it.
            bindings[other] = self
            return bindings
            
        # An Atom can only unify with a Var or another Atom.
        return False


class Var(object):
    """Represents a logic variable."""

    counter = 0 # for generating unused variables
    
    def __init__(self, var):
        self.var = var
        
    def __str__(self):
        return str(self.var)

    def __repr__(self):
        return 'Var(%s)' % repr(self.var)

    def __eq__(self, other):
        return isinstance(other, Var) and other.var == self.var

    def lookup(self, bindings):
        """Find the Atom (or None) that self is bound to in bindings."""
        binding = bindings.get(self)
        while isinstance(binding, Var):
            binding = bindings.get(binding)
        return binding
    
    def unify(self, other, bindings):
        """
        Unify self with other (if possible), returning the updated bindings.
        if self and other don't unify, returns False.
        """
        
        if isinstance(other, Atom):
            # Let Atom handle unification with Vars.
            return other.unify(self, bindings)

        if isinstance(other, Var):
            bindings = dict(bindings)
            
            # If two variables are identical, we can leave the bindings alone.
            if self == other:
                return bindings

            # Check if either of us are already bound to an Atom.
            self_bind = self.lookup(bindings)
            other_bind = other.lookup(bindings)
            
            # If both are unbound, bind them together.
            if not self_bind and not other_bind:
                bindings[self] = other
                bindings[other] = self
                return bindings

            # Otherwise, try to bind the unbound to the bound (if possible).
            if self_bind and not other_bind:
                bindings[other] = self
                return bindings
            if not self_bind and other_bind:
                bindings[self] = other
                return bindings
            
            # If both are bound, make sure they bind to the same Atom.
            if self_bind == other_bind:
                return bindings
            return False

        # A Var can only unify with an Atom or another Var.
        return False

    def rename(self):
        var = '%s%d' % (self.var, Var.counter)
        Var.counter += 1
        return Var(var)


class Relation(object):
    """A relationship (specified by a predicate) that holds between terms."""
    
    def __init__(self, pred, args):
        self.pred = pred
        self.args = args
        
    def __str__(self):
        return '%s(%s)' % (self.pred, ', '.join(map(str, self.args)))

    def __repr__(self):
        return 'Relation(%s, %s)' % (repr(self.pred), repr(self.args))

    def __eq__(self, other):
        return (isinstance(other, Relation)
                and self.pred == other.pred
                and list(self.args) == list(other.args))

    def unify(self, other, bindings):
        if not isinstance(other, Relation):
            return False

        if self.pred != other.pred:
            return False

        if len(self.args) != len(other.args):
            return False

        for i, term in enumerate(self.args):
            bindings = term.unify(other.args[i], bindings)
            if not bindings:
                return False

        return bindings

    def bind_vars(self, bindings):
        bound = []
        for arg in self.args:
            bound.append(arg.lookup(bindings) if arg in bindings else arg)
        return Relation(self.pred, bound)

    def rename_vars(self):
        renames = {}
        args = []
        for arg in self.args:
            if isinstance(arg, Var):
                args.append(renames.setdefault(arg, arg.rename()))
            else:
                args.append(arg)
        return Relation(self.pred, args)

    def get_vars(self):
        return [arg for arg in self.args if isinstance(arg, Var)]


class Clause(object):
    """A general clause with a head relation and some body relations."""
    
    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __repr__(self):
        return 'Clause(%s, %s)' % (repr(self.head), repr(self.body))

    def __eq__(self, other):
        return (isinstance(other, Clause)
                and self.head == other.head
                and list(self.body) == list(other.body))

    def unify(self, other, bindings):
        if not isinstance(other, Clause):
            return False

        bindings = self.head.unify(other.head, bindings)
        if not bindings:
            return False

        if len(self.body) != len(other.body):
            return False
        
        for i, relation in enumerate(self.body):
            bindings = relation.unify(other.body[i], bindings)
            if not bindings:
                return False

        return bindings

    def bind_vars(self, bindings):
        head = self.head.bind_vars(bindings)
        body = [r.bind_vars(bindings) for r in self.body]
        return Clause(head, body)

    def rename_vars(self):
        return Clause(self.head.rename_vars(),
                      [rel.rename_vars() for rel in self.body])

    def get_vars(self):
        vars = self.head.get_vars()
        for rel in self.body:
            vars.extend(rel.get_vars())
        return list(set(vars))
    

class Fact(Clause):
    """A relation whose truth is not dependent on any variable."""
    
    def __init__(self, relation):
        Clause.__init__(self, relation, [])

    def __repr__(self):
        return 'Fact(%s)' % repr(self.relation)

    def __str__(self):
        return str(self.head)


class Rule(Clause):
    """A clause where the head relation holds if the body relations do."""
    
    def __init__(self, head, body):
        Clause.__init__(self, head, body)

    def __repr__(self):
        return 'Rule(%s, %s)' % (repr(self.head), repr(self.body))

    def __str__(self):
        return '%s <= %s' % (str(self.head), ', '.join(map(str, self.body)))

    
## Idea 3: Automatic backtracking

def prove_all(goals, bindings, db):
    print '==========================='
    print 'Goals:', goals
    print 'Bindings:', bindings
    
    if bindings == False:
        return False
    if not goals:
        return bindings
    return prove(goals[0], bindings, goals[1:], db)


def prove(goal, bindings, others, db):
    print '==========================='
    print 'Goal:', goal
    print 'Bindings:', bindings
    print 'Rest:', others
    
    results = db.query(goal.pred)
    if not results:
        return False

    if not isinstance(results, list):
        # If the retrieved data from the database isn't a list of clauses,
        # it must be a primitive.
        return results(goal.args, bindings, others, db)

    # results is a list of clauses whose head relation has the same predicate
    # as the predicate of goal.
    for clause in results:
        # Each clause retrieved from the database might help us prove goal.
        print 'Considering clause', clause
        
        # First, rename the variables in clause so they don't collide with
        # those in goal.
        renamed = clause.rename_vars()
        if not renamed:
            continue

        # Next, we try to unify goal with the head of the candidate clause.
        # If unification is possible, then the candidate clause might either be
        # a rule that can prove goal or a fact that states goal is already true.
        unified = goal.unify(renamed.head, bindings)
        if not unified:
            continue

        print 'It unified:', unified
        
        # We need to prove the subgoals of the candidate clause before using
        # it to prove goal.
        subgoals = renamed.body + others
        
        proved = prove_all(subgoals, unified, db)
        if proved:
            return proved

    return False


def display_bindings(vars, bindings, goals, db):
    if not vars:
        print 'Yes'
    print 'vars', vars
    for var in vars:
        print var, var.lookup(bindings)
    if should_continue():
        return False
    return prove_all(goals, bindings, db)


def should_continue():
    yes = raw_input()
    if yes == ';':
        return True
    return False


def prolog_prove(goals, db):
    db.define_primitive('display_bindings', display_bindings)
    vars = reduce(lambda x, y: x + y, [clause.get_vars() for clause in goals])
    prove_all(goals + [Relation('display_bindings', vars)], {}, db)
    print 'No'