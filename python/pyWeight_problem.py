'''
pyWeight_problem

Holds the weightProblem class for weightandbalance solvers.

Copyright (c) 2015 by Dr. Charles A. Mader 
All rights reserved. Not to be used for commercial purposes.
Revision: 1.0   $Date: 16/08/2015 21:00$


Developers:
-----------
- Dr. Charles A. Mader (CM)

History
-------
	v. 1.0 - Initial Class Creation (CM, 2015)

'''

import sys, numpy, copy
import warnings


class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| WeightProblem Error: '
        i = 23
        for word in message.split():
            if len(word) + i + 1 > 78: # Finish line and start new one
                msg += ' '*(78-i)+'|\n| ' + word + ' '
                i = 1 + len(word)+1
            else:
                msg += word + ' '
                i += len(word)+1
        msg += ' '*(78-i) + '|\n' + '+'+'-'*78+'+'+'\n'
        print(msg)
        Exception.__init__(self)


class WeightProblem(object):
    '''
    Weight Problem Object:

    This Weight Problem Object should contain all of the information required
    to estimate the weight of a particular component configuration.

    Parameters
    ----------
    
    name : str
        A name for the configuration

    units : str
        Define the units that this weight problem will use. This set of units is transferred to all components when the are added to the weight problem. It is assumed that all user defined parameters provided to the components are in this unit system. Each component converts the user provided inputs from this unit system to the one used internally to perform calculations and then converts the output back to the user defined system.
    
    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this weight 
        problem
    '''

    def __init__(self, name, units,**kwargs):
        """
        Initialize the mission problem
        """
        self.name=name
        self.units = units.lower()
        
        self.components = {}
        self.fuelcases = []
        self.funcNames = {}
        self.currentDVs = {}
        self.solveFailed = False

        # Check for function list:
        self.evalFuncs = set()
        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])
            
    def addComponents(self, components): #*components?
        '''
        Append a list of components to the interal component list
        '''

        # Check if components is of type Component or list, otherwise raise Error
        if type(components) == list:
            pass
        elif type(components) == object:
            components = [components]
        else:
            raise Error('addComponents() takes in either a list of or a single component')

        # Add the components to the internal list
        for comp in components:
            comp.setUnitSystem(self.units)
            self.components[comp.name]=comp

            for dvName in comp.DVs:
                key = self.name+'_'+dvName
                self.currentDVs[key] = comp.DVs[dvName].value
            # end

        return

    def _getNumComponents(self):
        '''
        This is a call that should only be used by MissionAnalysis
        '''
        return len(self.components)


    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
            """
        
        for compKey in self.components.keys():
            comp= self.components[compKey]
            for key in comp.DVs:
                dvName = self.name+'_'+key
                
                if dvName in x:
                    #print key,x[dvName]
                    xTmp = {key:x[dvName]}
                    comp.setDesignVars(xTmp)
                    self.currentDVs[dvName]=x[dvName]

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name+'_'+key
                
                if dvName in x:
                    #print key,x[dvName]
                    xTmp = {key:x[dvName]}
                    case.setDesignVars(xTmp)
                    self.currentDVs[dvName]=x[dvName]
             
        #print 'currentDVs',self.currentDVs

    def addVariablesPyOpt(self, optProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
            """

        for compKey in self.components.keys():
            comp= self.components[compKey]
            for key in comp.DVs:
                dvName = self.name+'_'+key
                dv = comp.DVs[key]
                if dv.addToPyOpt:
                    optProb.addVar(dvName, 'c', value=dv.value, lower=dv.lower,
                                   upper=dv.upper, scale=dv.scale)

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name+'_'+key
                
                dv = case.DVs[key]
                if dv.addToPyOpt:
                    optProb.addVar(dvName, 'c', value=dv.value, lower=dv.lower,
                                   upper=dv.upper, scale=dv.scale)

    def getVarNames(self):
        '''
        Get the variable names associate with this weight problem
        '''

        names = []
        for compKey in self.components.keys():
            comp= self.components[compKey]
            for key in comp.DVs:
                dvName = self.name+'_'+key
                names.append(dvName)

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name+'_'+key
                names.append(dvName)

        return names

    def addConstraintsPyOpt(self,optProb):
        """
        Add the linear constraints for each of the fuel cases.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """
        for case in self.fuelcases:
            case.addLinearConstraint(optProb,self.name)

    def addFuelCases(self, cases):
        '''
        Append a list of fuel cases to the weight problem
        '''

        # Check if case is a single entry or a list, otherwise raise Error
        if type(cases) == list:
            pass
        elif type(cases) == object:
            cases = [cases]
        else:
            raise Error('addFuelCases() takes in either a list of or a single fuelcase')
            
        # Add the fuel cases to the problem
        for case in cases:
            self.fuelcases.append(case)

            for dvName in case.DVs:
                key = self.name+'_'+dvName
                self.currentDVs[key] = case.DVs[dvName].value
            # end
        return

    def _getComponentKeys(self, include=None, exclude=None, 
                          includeType=None, excludeType=None):
        '''
        Get a list of component keys based on inclusion and exclusion

        Parameters
        ----------
        include : list or str
           (Optional) String or list of components to be included in the sum
        exclude : list or str
           (Optional) String or list of components to be excluded in the sum
        includeType : 
           (Optional) String or list of component types to include in the weight keys
        excludeType :
           (Optional) String or list of component types to exclude in the weight keys
        '''

        weightKeys = set(self.components.keys())

        if includeType != None:
            # Specified a list of component types to include
            if type(includeType) == str:
                includeType = [includeType]
            weightKeysTmp = set()
            for key in weightKeys:
                if self.components[key].compType in includeType:
                    weightKeysTmp.add(key)
            weightKeys = weightKeysTmp

        if include != None:
            # Specified a list of compoents to include
            if type(include) == str:
                include = [include]
            include = set(include)
            weightKeys.intersection_update(include)

        if exclude != None:
            # Specified a list of components to exclude
            if type(exclude) == str:
                exclude = [exclude]
            exclude = set(exclude)
            weightKeys.difference_update(exclude)

        if excludeType != None:
            # Specified a list of compoent types to exclude
            if type(excludeType) == str:
                excludeType = [excludeType]
            weightKeysTmp = copy.copy(weightKeys)
            for key in weightKeys:
                if self.components[key].compType in excludeType:
                    weightKeysTmp.remove(key)
            weightKeys = weightKeysTmp

        return weightKeys


    def writeMassesTecplot(self,filename):
        '''
        Get a list of component keys based on inclusion and exclusion

        Parameters
        ----------
        
        filename: str
            filename for writing the masses. This string will have the
            .dat suffix appended to it.
        '''
        
        fileHandle = filename+'.dat'
        f = open(fileHandle,'w')
        nMasses = len(self.nameList)
        f.write('TITLE = "%s: Mass Data"\n'%self.name)
        f.write('VARIABLES = "X", "Y", "Z", "Mass"\n')
        locList = ['current','fwd','aft']

        for loc in locList:
            f.write('ZONE T="%s", I=%d, J=1, K=1, DATAPACKING=POINT\n'%(loc,nMasses))

            for key in self.components.keys():
                CG = self.components[key].getCG(loc)
                mass =  self.components[key].getMass()
                x= numpy.real(CG[0])
                y= numpy.real(CG[1])
                z= numpy.real(CG[2])
                m= numpy.real(mass)

                f.write('%f %f %f %f\n'%(x,y,z,m))
               
            # end
            f.write('\n')
        # end
            
        # textOffset = 0.5
        # for loc in locList:
        #     for name in self.nameList:
        #         x= numpy.real(self.componentDict[name].CG[loc][0])
        #         y= numpy.real(self.componentDict[name].CG[loc][1])
        #         z= numpy.real(self.componentDict[name].CG[loc][2])+textOffset
        #         m= numpy.real(self.componentDict[name].W)

        #         f.write('TEXT CS=GRID3D, HU=POINT, X=%f, Y=%f, Z=%f, H=12, T="%s"\n'%(x,y,z,name+' '+loc))
        #     # end
            
        # # end


        f.close()
        return        

    def writeProblemData(self,fileName):
        '''
        Write the problem data to a file
        '''
        fileHandle = fileName+'.txt'
        f = open(fileHandle,'w')
        f.write('Name, W, Mass, CG \n')
        for key in sorted(self.components.keys()):
            CG = self.components[key].getCG(self.units,'current')
            mass =  self.components[key].getMass(self.units)
            W =  self.components[key].getWeight(self.units)
            name = self.components[key].name
            f.write('%s: %f, %f, %f %f %f \n'%(name,W,mass,CG[0],CG[1],CG[2]))
        # end

        f.close()
        return
            

    def __str__(self):
        '''
        loop over the components and call the owned print function
        '''
        for key in self.components.keys():
            print key
            print self.components[key]
        # end
        
        return ' '


        # self.printComponentData()
        # return 'Print statement for WeightAndBalance not implemented'




class FuelCase(object):
    '''
    class to handle individual fuel cases.
    '''
    def __init__(self, name, fuelFraction=.9, reserveFraction = .1):
        '''
        Initialize the fuel case

        Parameters
        ----------
    
        name : str
           A name for the fuel case. 
    
        fuelFraction : float
           Fraction of fuel component volume that contains fuel.

        reserveFraction : float
           Fraction of fuel component volume that contains reserve fuel.
        '''

        self.name=name
        self.fuelFraction = fuelFraction
        self.reserveFraction = reserveFraction

        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}
        self.possibleDVs = ['fuelFraction','reserveFraction']
        
        return

    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0,
              name=None, offset=0.0,axis=None, addToPyOpt=True):

        """
        Add one of the fuel case parameters as a weight and balance design
        variable. Typical variables are fuelfraction and reservefraction.
        An error will be given if the requested DV is not allowed to 
        be added .
      

        Parameters
        ----------
        key : str
            Name of variable to add. See above for possible ones

        value : float. Default is None
            Initial value for variable. If not given, current value
            of the attribute will be used.

        lower : float. Default is None
            Optimization lower bound. Default is unbounded.

        upper : float. Default is None
            Optimization upper bound. Default is unbounded.

        scale : float. Default is 1.0
            Set scaling parameter for the optimization to use.

        name : str. Default is None
            Overwrite the name of this variable. This is typically
            only used when the user wishes to have multiple
            components explictly use the same design variable.

        offset : float. Default is 0.0

            Specify a specific (constant!) offset of the value used,
            as compared to the actual design variable.

        addToPyOpt : bool. Default True. 
            Flag specifying if this variable should be added. Normally this 
            is True. However, if there are multiple weightProblems sharing
            the same variable, only one needs to add the variables to pyOpt
            and the others can set this to False. 

        Examples
        --------
        >>> # Add W variable with typical bounds
        >>> fuelCase.addDV('fuelFraction', value=0.5, lower=0.0, upper=1.0, scale=0.1)
        >>> fuelCase.addDV('reserveFraction', value=0.1, lower=0.0, upper=1.0, scale=0.1)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error('The DV \'%s\' could not be added.  The list of possible DVs are: %s.'% (
                            key, repr(self.possibleDVs)))

        if name is None:
            dvName = '%s_'% self.name + key 
        else:
            dvName = name

        if axis is not None:
            dvName+='_%s'%axis

        if value is None:
            value = getattr(self, key)

        self.DVs[dvName] = fuelCaseDV(key, value, lower, upper, scale, offset, addToPyOpt)
        self.DVNames[key] = dvName


    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
            """

        for key in self.DVNames:
            dvName = self.DVNames[key]
            if dvName in x:
                setattr(self, key, x[dvName] + self.DVs[dvName].offset)
                self.DVs[dvName].value = x[dvName]

    def addLinearConstraint(self,optProb,prefix):
        '''
        add the linear constraint for the fuel fractions
        '''
        reserveDV = False
        fuelDV = False
        for key in self.DVNames:
            if key.lower()=='fuelfraction':
                fuelDV = True

            if key.lower()=='reservefraction':
                reserveDV = True

        conName = prefix+'_'+self.name+'_fuelcase'
        var1Name = prefix+'_'+self.name+'_fuelFraction'
        var2Name = prefix+'_'+self.name+'_reserveFraction'
        if reserveDV and fuelDV:
            optProb.addCon(conName,lower=0,upper=1,scale=1,linear=True,wrt=[var1Name,var2Name],jac={var1Name:[[1]], var2Name:[[1]]})
        elif reserveDV:
            optProb.addCon(conName,lower=0,upper=1-self.fuelFraction,scale=1,linear=True,wrt=[var2Name],jac={var2Name:[[1]]})
        elif fuelDV:
            optProb.addCon(conName,lower=0,upper=1-self.reserveFraction,scale=1,linear=True,wrt=[var1Name],jac={var1Name:[[1]]})





class fuelCaseDV(object):
    """
    A container storing information regarding a fuel case variable.
    """
    def __init__(self, key, value, lower, upper, scale, offset, addToPyOpt):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset    
        self.addToPyOpt = addToPyOpt
